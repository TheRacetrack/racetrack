package main

import (
	"fmt"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
	uuid "github.com/satori/go.uuid"
)

func proxyEndpoint(c *gin.Context, cfg *Config, jobPath string) {
	startTime := time.Now()

	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})

	logger.Info("Incoming Proxy request", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleProxyRequest(c, cfg, logger, requestId, jobPath)
	if err != nil {
		metricJobProxyRequestErros.Inc()
		errorStr := err.Error()
		logger.Error("Proxy request error", log.Ctx{
			"status": statusCode,
			"error":  errorStr,
			"path":   c.Request.URL.Path,
		})
		c.JSON(statusCode, gin.H{
			"error":     fmt.Sprintf("Proxy request error: %s", errorStr),
			"status":    http.StatusText(statusCode),
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
) (int, error) {

	if cfg.RemoteGatewayMode {
		return handleSlaveProxyRequest(c, cfg, logger, requestId, jobPath)
	}

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

	authToken := getAuthFromHeaderOrCookie(c.Request)
	lifecycleClient := NewLifecycleClient(cfg.LifecycleUrl, authToken,
		cfg.LifecycleToken, cfg.RequestTracingHeader, requestId)
	var job *JobDetails
	var callerName string
	var err error

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
				return http.StatusUnauthorized, errors.Wrap(err, "Unauthenticated")
			} else {
				return http.StatusUnauthorized, errors.New("Unauthenticated")
			}
		} else if errors.As(err, &NotFoundError{}) {
			return http.StatusNotFound, errors.Wrap(err, "Job was not found")
		}
		return http.StatusInternalServerError, errors.Wrap(err, "Getting job details")
	}

	metricJobProxyRequests.WithLabelValues(job.Name, job.Version).Inc()

	if jobCall.RemoteGatewayUrl != nil {
		return handleMasterProxyRequest(c, cfg, logger, requestId, jobPath, jobCall, job, callerName)
	}

	targetUrl := TargetURL(cfg, job, c.Request.URL.Path)
	ServeReverseProxy(targetUrl, c, job, cfg, logger, requestId, callerName)
	return 200, nil
}

func ServeReverseProxy(
	target url.URL,
	c *gin.Context,
	job *JobDetails,
	cfg *Config,
	logger log.Logger,
	requestId string,
	callerName string,
) {

	director := func(req *http.Request) {
		req.URL.Scheme = target.Scheme
		req.URL.Host = target.Host
		req.URL.Path = target.Path
		req.Host = c.Request.Host
		req.Header.Add("X-Forwarded-Host", req.Host)
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
		})
		statusCode := strconv.Itoa(res.StatusCode)
		metricJobProxyResponseCodes.WithLabelValues(job.Name, job.Version, statusCode).Inc()
		return nil
	}

	errorHandler := func(res http.ResponseWriter, req *http.Request, err error) {
		errorStr := err.Error()
		logger.Error("Reverse proxy error", log.Ctx{
			"jobName":    job.Name,
			"jobVersion": job.Version,
			"jobStatus":  job.Status,
			"caller":     callerName,
			"host":       target.Host,
			"path":       target.Path,
			"error":      errorStr,
		})
		c.JSON(http.StatusBadGateway, gin.H{
			"error":      fmt.Sprintf("Reverse proxy error: %s", errorStr),
			"status":     http.StatusText(http.StatusBadGateway),
			"jobName":    job.Name,
			"jobVersion": job.Version,
			"jobStatus":  job.Status,
			"requestId":  requestId,
			"caller":     callerName,
		})
		metricJobProxyErrors.Inc()
	}

	proxy := &httputil.ReverseProxy{
		Director:       director,
		ModifyResponse: modifyResponse,
		ErrorHandler:   errorHandler,
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
