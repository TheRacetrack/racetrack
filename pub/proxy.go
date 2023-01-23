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

func proxyEndpoint(c *gin.Context, cfg *Config) {
	startTime := time.Now()

	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})

	logger.Info("Incoming Proxy request", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleProxyRequest(c, cfg, logger, requestId)
	if err != nil {
		metricFatmanProxyRequestErrors.Inc()
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
	metricOverallFatmanProxyResponseTime.Add(time.Since(startTime).Seconds())
}

func handleProxyRequest(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	requestId string,
) (int, error) {

	if c.Request.Method != "POST" && c.Request.Method != "GET" {
		c.Writer.Header().Set("Allow", "GET, POST")
		return http.StatusMethodNotAllowed, errors.New("Method not allowed")
	}

	fatmanName := c.Param("fatman")
	if fatmanName == "" {
		return http.StatusBadRequest, errors.New("Couldn't extract fatman name")
	}

	fatmanVersion := c.Param("version")
	if fatmanVersion == "" {
		return http.StatusBadRequest, errors.New("Couldn't extract fatman version")
	}

	if c.Request.Header.Get("Accept") == "" {
		return http.StatusBadRequest, errors.New("Missing 'Accept' header. " +
			"You might wanted to include 'Accept: application/json, */*' request header.")
	}

	fatmanPath := c.Param("path")

	authToken := getAuthFromHeaderOrCookie(c.Request)
	lifecycleClient := NewLifecycleClient(cfg.LifecycleUrl, authToken,
		cfg.LifecycleToken, cfg.RequestTracingHeader, requestId)

	fatman, err := lifecycleClient.GetFatmanDetails(fatmanName, fatmanVersion)
	if err != nil {
		if errors.Is(err, FatmanNotFound) {
			return http.StatusNotFound, err
		}
		return http.StatusInternalServerError, errors.Wrap(err, "failed to get Fatman details")
	}

	metricFatmanProxyRequests.WithLabelValues(fatmanName, fatman.Version).Inc()

	if cfg.AuthRequired {
		err := lifecycleClient.AuthenticateCaller(c.Request.URL.Path, fatmanName, fatman.Version, fatmanPath, cfg.AuthDebug)
		if err == nil {
			metricAuthSuccessful.Inc()
		} else {
			metricAuthFailed.Inc()
			if errors.As(err, &AuthenticationFailure{}) {
				return http.StatusUnauthorized, errors.Wrap(err, "Unauthenticated")
			}
			return http.StatusInternalServerError, errors.Wrap(err, "Checking authentication error")
		}
	}

	targetUrl := TargetURL(cfg, fatman, c.Request.URL.Path)
	ServeReverseProxy(targetUrl, c, fatman, cfg, logger, requestId)
	return 200, nil
}

func ServeReverseProxy(
	target url.URL,
	c *gin.Context,
	fatman *FatmanDetails,
	cfg *Config,
	logger log.Logger,
	requestId string,
) {

	director := func(req *http.Request) {
		req.URL.Scheme = target.Scheme
		req.URL.Host = target.Host
		req.URL.Path = target.Path
		req.Host = c.Request.Host
		req.Header.Add("X-Forwarded-Host", req.Host)
		req.Header.Set(cfg.RequestTracingHeader, requestId)
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
			"fatmanName":    fatman.Name,
			"fatmanVersion": fatman.Version,
			"fatmanPath":    target.Path,
			"status":        res.StatusCode,
		})
		statusCode := strconv.Itoa(res.StatusCode)
		metricFatmanProxyResponseCodes.WithLabelValues(fatman.Name, fatman.Version, statusCode).Inc()
		return nil
	}

	errorHandler := func(res http.ResponseWriter, req *http.Request, err error) {
		errorStr := err.Error()
		logger.Error("Reverse proxy error", log.Ctx{
			"fatmanName":    fatman.Name,
			"fatmanVersion": fatman.Version,
			"fatmanStatus":  fatman.Status,
			"host":          target.Host,
			"path":          target.Path,
			"error":         errorStr,
		})
		c.JSON(http.StatusBadGateway, gin.H{
			"error":         fmt.Sprintf("Reverse proxy error: %s", errorStr),
			"status":        http.StatusText(http.StatusBadGateway),
			"fatmanName":    fatman.Name,
			"fatmanVersion": fatman.Version,
			"fatmanStatus":  fatman.Status,
			"requestId":     requestId,
		})
		metricFatmanProxyErrors.Inc()
	}

	proxy := &httputil.ReverseProxy{
		Director:       director,
		ModifyResponse: modifyResponse,
		ErrorHandler:   errorHandler,
	}

	metricFatmanProxyRequestsStarted.WithLabelValues(fatman.Name, fatman.Version).Inc()
	fatmanCallStartTime := time.Now()

	proxy.ServeHTTP(c.Writer, c.Request)

	fatmanCallTime := time.Since(fatmanCallStartTime).Seconds()
	metricFatmanCallResponseTimeHistogram.WithLabelValues(fatman.Name, fatman.Version).Observe(fatmanCallTime)
	metricFatmanCallResponseTime.WithLabelValues(fatman.Name, fatman.Version).Add(fatmanCallTime)
	metricFatmanProxyRequestsDone.WithLabelValues(fatman.Name, fatman.Version).Inc()
}

func getRequestTracingId(req *http.Request, headerName string) string {
	tracingId := req.Header.Get(headerName)
	if tracingId != "" {
		return tracingId
	}
	return uuid.NewV4().String()
}
