package main

import (
	"net/http"
	"net/http/httputil"
	"net/url"
	"strconv"
	"time"

	"github.com/gorilla/mux"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
	uuid "github.com/satori/go.uuid"
)

func proxyEndpoint(res http.ResponseWriter, req *http.Request, cfg *Config) {
	startTime := time.Now()

	requestId := getRequestTracingId(req, cfg.RequestTracingHeader)
	traceId := req.Header.Get(cfg.RequestTracingHeader + "-trace-id")
	spanId := req.Header.Get(cfg.RequestTracingHeader + "-span-id")
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})

	logger.Info("Incoming Proxy request", log.Ctx{"method": req.Method, "path": req.URL.Path})
	statusCode, err := handleProxyRequest(res, req, cfg, logger, requestId, traceId, spanId)
	if err != nil {
		metricFatmanProxyRequestErrors.Inc()
		errorStr := err.Error()
		logger.Error("Proxy request error", log.Ctx{
			"status": statusCode,
			"error":  errorStr,
			"path":   req.URL.Path,
		})
		http.Error(res, errorStr, statusCode)
	}
	metricOverallFatmanProxyResponseTime.Add(time.Since(startTime).Seconds())
}

func handleProxyRequest(
	res http.ResponseWriter,
	req *http.Request,
	cfg *Config,
	logger log.Logger,
	requestId, traceId, spanId string,
) (int, error) {
	if req.Method != "POST" && req.Method != "GET" {
		res.Header().Set("Allow", "GET, POST")
		return http.StatusMethodNotAllowed, errors.New("Method not allowed")
	}

	vars := mux.Vars(req)
	fatmanName := vars["fatman"]
	if fatmanName == "" {
		return http.StatusBadRequest, errors.New("Couldn't extract fatman name")
	}

	fatmanVersion := vars["version"]
	if fatmanVersion == "" {
		return http.StatusBadRequest, errors.New("Couldn't extract fatman version")
	}

	if req.Header.Get("Accept") == "" {
		return http.StatusBadRequest, errors.New("Missing 'Accept' header. " +
			"You might wanted to include 'Accept: application/json, */*' request header.")
	}

	fatmanPath := vars["path"]

	authToken := getAuthFromHeaderOrCookie(req)
	lifecycleClient := NewLifecycleClient(cfg.LifecycleUrl, authToken,
		cfg.LifecycleToken, cfg.RequestTracingHeader, requestId, traceId, spanId)

	fatman, err := lifecycleClient.GetFatmanDetails(fatmanName, fatmanVersion)
	if err != nil {
		if errors.Is(err, FatmanNotFound) {
			return http.StatusNotFound, err
		}
		return http.StatusInternalServerError, errors.Wrap(err, "failed to get Fatman details")
	}

	metricFatmanProxyRequests.WithLabelValues(fatmanName, fatman.Version).Inc()

	if cfg.AuthRequired {
		err := lifecycleClient.AuthenticateCaller(req.URL.Path, fatmanName, fatman.Version, fatmanPath, cfg.AuthDebug)
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

	targetUrl := TargetURL(cfg, fatman, req.URL.Path)
	ServeReverseProxy(targetUrl, res, req, fatmanName, fatman.Version, cfg, logger, requestId)
	return 200, nil
}

func ServeReverseProxy(
	target url.URL,
	res http.ResponseWriter,
	pubReq *http.Request,
	fatmanName, fatmanVersion string,
	cfg *Config,
	logger log.Logger,
	requestId string,
) {

	director := func(req *http.Request) {
		req.URL.Scheme = target.Scheme
		req.URL.Host = target.Host
		req.URL.Path = target.Path
		req.Host = pubReq.Host
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
			"fatmanName":    fatmanName,
			"fatmanVersion": fatmanVersion,
			"fatmanPath":    target.Path,
			"status":        res.StatusCode,
		})
		statusCode := strconv.Itoa(res.StatusCode)
		metricFatmanProxyResponseCodes.WithLabelValues(fatmanName, fatmanVersion, statusCode).Inc()
		return nil
	}

	errorHandler := func(res http.ResponseWriter, req *http.Request, err error) {
		logger.Error("Reverse proxy error", log.Ctx{
			"fatmanName":    fatmanName,
			"fatmanVersion": fatmanVersion,
			"host":          target.Host,
			"path":          target.Path,
			"error":         err.Error(),
		})
		metricFatmanProxyErrors.Inc()
	}

	proxy := &httputil.ReverseProxy{
		Director:       director,
		ModifyResponse: modifyResponse,
		ErrorHandler:   errorHandler,
	}

	metricFatmanProxyRequestsStarted.WithLabelValues(fatmanName, fatmanVersion).Inc()
	fatmanCallStartTime := time.Now()

	proxy.ServeHTTP(res, pubReq)

	fatmanCallTime := time.Since(fatmanCallStartTime).Seconds()
	metricFatmanCallResponseTimeHistogram.WithLabelValues(fatmanName, fatmanVersion).Observe(fatmanCallTime)
	metricFatmanCallResponseTime.WithLabelValues(fatmanName, fatmanVersion).Add(fatmanCallTime)
	metricFatmanProxyRequestsDone.WithLabelValues(fatmanName, fatmanVersion).Inc()
}

func getRequestTracingId(req *http.Request, headerName string) string {
	tracingId := req.Header.Get(headerName)
	if tracingId != "" {
		return tracingId
	}
	return uuid.NewV4().String()
}
