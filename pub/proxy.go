package main

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strconv"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
	uuid "github.com/satori/go.uuid"
)

var defaultJobProxyTransport http.RoundTripper = defaultHttpTransport()

func proxyEndpoint(c *gin.Context, cfg *Config, jobPath string) {
	startTime := time.Now()

	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})

	logger.Info("Incoming Proxy request", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleProxyRequest(c, cfg, logger, requestId, jobPath, startTime)
	if err != nil {
		metricJobProxyRequestErrors.Inc()
		errorStr := err.Error()
		logger.Error("Proxy request error", log.Ctx{
			"status":   statusCode,
			"error":    errorStr,
			"path":     c.Request.URL.Path,
			"duration": time.Since(startTime).String(),
		})
		c.JSON(statusCode, gin.H{
			"error":     fmt.Sprintf("Proxy request error: %s", errorStr),
			"requestId": requestId,
		})
	}
	metricOverallJobProxyResponseTime.Add(time.Since(startTime).Seconds())
}

func handleProxyRequest(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	requestId string,
	jobPath string,
	startTime time.Time,
) (int, error) {

	if c.Request.Method != "POST" && c.Request.Method != "GET" {
		c.Writer.Header().Set("Allow", "GET, POST")
		return http.StatusMethodNotAllowed, errors.New("Method not allowed")
	}

	jobName := c.Param("job")
	if jobName == "" {
		return http.StatusBadRequest, errors.New("Couldn't extract job name")
	}

	jobVersion := c.Param("version")
	if jobVersion == "" {
		return http.StatusBadRequest, errors.New("Couldn't extract job version")
	}

	if c.Request.Header.Get("Accept") == "" {
		return http.StatusBadRequest, errors.New("Missing 'Accept' header. " +
			"You might wanted to include 'Accept: application/json, */*' request header.")
	}

	job, jobCall, callerName, statusCode, err := getAuthorizedJobDetails(c, cfg, requestId, jobName, jobVersion, jobPath)
	if err != nil {
		if statusCode == http.StatusNotFound {
			logger.Warn("Job was not found", log.Ctx{
				"status":   statusCode,
				"error":    err.Error(),
				"path":     c.Request.URL.Path,
				"duration": time.Since(startTime).String(),
			})
			c.JSON(statusCode, gin.H{
				"error":     fmt.Sprintf("Proxy request error: %s", err.Error()),
				"requestId": requestId,
			})
			return statusCode, nil
		}
		metricLifecycleErrors.Inc()
		return statusCode, err
	}

	metricJobProxyRequests.WithLabelValues(job.Name, job.Version).Inc()

	if !cfg.RemoteGatewayMode && jobCall.RemoteGatewayUrl != nil {
		return handleMasterProxyRequest(c, cfg, logger, requestId, jobPath, jobCall, job, callerName, startTime)
	}

	urlPath := JoinURL("/pub/job/", job.Name, job.Version, jobPath)
	targetUrl := TargetURL(cfg, job, urlPath)

	ServeReverseProxy(targetUrl, c, job, cfg, logger, requestId, callerName, startTime)
	return http.StatusOK, nil
}

func NewProxyLifecycleClient(
	cfg *Config,
	authToken string,
	requestId string,
) (LifecycleClient, error) {
	if cfg.RemoteGatewayMode {
		return NewRemoteLifecycleClient(authToken, requestId)
	} else {
		return NewMasterLifecycleClient(cfg.LifecycleUrl, authToken,
			cfg.LifecycleToken, cfg.RequestTracingHeader, requestId), nil
	}
}

func ServeReverseProxy(
	target url.URL,
	c *gin.Context,
	job *JobDetails,
	cfg *Config,
	logger log.Logger,
	requestId string,
	callerName string,
	startTime time.Time,
) {

	director := func(req *http.Request) {
		req.URL.Scheme = target.Scheme
		req.URL.Host = target.Host
		req.URL.Path = target.Path
		req.Header.Add("X-Forwarded-Host", req.Host)
		req.Host = target.Host
		req.Header.Set(cfg.RequestTracingHeader, requestId)
		if callerName != "" {
			req.Header.Set(cfg.CallerNameHeader, callerName)
		}
		req.RequestURI = ""
	}

	modifyResponse := func(res *http.Response) error {
		// Transform redirect links to relative (without hostname).
		// Target server doesn't know it's being proxied so it tries to redirect to internal URL.
		location := res.Header.Get("Location")
		if location != "" {
			redirectUrl, err := url.Parse(location)
			if err == nil {
				redirectUrl.Host = ""
				redirectUrl.Scheme = ""
				res.Header.Set("Location", redirectUrl.String())
			}
		}

		res.Header.Set(cfg.RequestTracingHeader, requestId)
		logger.Info("Proxy request done", log.Ctx{
			"jobName":    job.Name,
			"jobVersion": job.Version,
			"jobPath":    target.Path,
			"caller":     callerName,
			"status":     res.StatusCode,
			"duration":   time.Since(startTime).String(),
		})
		statusCode := strconv.Itoa(res.StatusCode)
		metricJobProxyResponseCodes.WithLabelValues(job.Name, job.Version, statusCode).Inc()
		return nil
	}

	errorHandler := func(res http.ResponseWriter, req *http.Request, err error) {
		metricJobProxyErrors.Inc()
		if errors.Is(err, io.EOF) {
			err = WrapError("connection broken to a target job (job may have died)", err)
			metricJobProxyConnectionBrokenErrors.Inc()
		} else if errors.Is(err, syscall.ECONNREFUSED) {
			err = WrapError("connection refused to a target job (job may be dead)", err)
			metricJobProxyConnectionRefusedErrors.Inc()
		} else if errors.Is(err, context.Canceled) {
			err = WrapError("client (or proxy timeout) canceled the request", err)
			metricJobProxyContextCanceledErrors.Inc()
		} else if errors.Is(err, context.DeadlineExceeded) {
			err = WrapError("request to a job timed out", err)
			metricJobProxyContextDeadlineErrors.Inc()
		}
		logger.Error("Reverse proxy error", log.Ctx{
			"jobName":    job.Name,
			"jobVersion": job.Version,
			"jobStatus":  job.Status,
			"caller":     callerName,
			"host":       target.Host,
			"path":       target.Path,
			"error":      err.Error(),
			"duration":   time.Since(startTime).String(),
		})
		c.JSON(http.StatusBadGateway, gin.H{
			"error":      fmt.Sprintf("Reverse proxy error: %s", err.Error()),
			"jobName":    job.Name,
			"jobVersion": job.Version,
			"jobStatus":  job.Status,
			"requestId":  requestId,
			"caller":     callerName,
		})
	}

	proxy := &httputil.ReverseProxy{
		Director:       director,
		ModifyResponse: modifyResponse,
		ErrorHandler:   errorHandler,
		Transport:      defaultJobProxyTransport,
	}

	metricJobProxyRequestsStarted.WithLabelValues(job.Name, job.Version).Inc()
	jobCallStartTime := time.Now()

	proxy.ServeHTTP(c.Writer, c.Request)

	jobCallTime := time.Since(jobCallStartTime).Seconds()
	metricJobCallResponseTimeHistogram.WithLabelValues(job.Name, job.Version).Observe(jobCallTime)
	metricJobCallResponseTime.WithLabelValues(job.Name, job.Version).Add(jobCallTime)
	metricJobProxyRequestsDone.WithLabelValues(job.Name, job.Version).Inc()
}

func getRequestTracingId(req *http.Request, headerName string) string {
	tracingId := req.Header.Get(headerName)
	if tracingId != "" {
		return tracingId
	}
	return uuid.NewV4().String()
}

// Authorize Job call and get job's details
func getAuthorizedJobDetails(
	c *gin.Context,
	cfg *Config,
	requestId string,
	jobName string,
	jobVersion string,
	jobPath string,
) (*JobDetails, *JobCallAuthData, string, int, error) {
	authToken := getAuthFromHeaderOrCookie(c.Request)

	lifecycleClient, err := NewProxyLifecycleClient(cfg, authToken, requestId)
	if err != nil {
		return nil, nil, "", http.StatusInternalServerError, err
	}

	var job *JobDetails
	var callerName string
	jobCall, err := lifecycleClient.AuthorizeCaller(jobName, jobVersion, jobPath)
	if err == nil {
		job = jobCall.Job
		if jobCall.Caller != nil {
			callerName = *jobCall.Caller
		}
		metricAuthSuccessful.Inc()
	} else {
		metricAuthFailed.Inc()
		if errors.As(err, &AuthenticationFailure{}) {
			if cfg.AuthDebug {
				return nil, nil, "", http.StatusUnauthorized, errors.Wrap(err, "Unauthenticated")
			} else {
				return nil, nil, "", http.StatusUnauthorized, errors.New("Unauthenticated")
			}
		} else if errors.As(err, &NotFoundError{}) {
			return nil, nil, "", http.StatusNotFound, errors.Wrap(err, "Job was not found")
		} else if errors.As(err, &ServiceUnavailableError{}) {
			return nil, nil, "", http.StatusServiceUnavailable, err
		}
		return nil, nil, "", http.StatusInternalServerError, errors.Wrap(err, "Getting job details")
	}

	return job, jobCall, callerName, http.StatusOK, nil
}
