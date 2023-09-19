package main

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

func remoteForwardEndpoint(c *gin.Context, cfg *Config, jobPath string) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})

	logger.Info("Incoming forwarding request from main Pub", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleRemoteForwardRequest(c, cfg, logger, requestId, jobPath)
	if err != nil {
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
}

func handleRemoteForwardRequest(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	requestId string,
	jobPath string,
) (int, error) {
	if !cfg.RemoteGatewayMode {
		return http.StatusUnauthorized, errors.New("Forwarding endpoint is only available in remote gateway mode")
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

	gatewayToken := c.Request.Header.Get(RemoteGatewayTokenHeader)
	if gatewayToken == "" {
		return http.StatusUnauthorized, errors.Errorf("Pub gateway expects token in %s header", RemoteGatewayTokenHeader)
	}
	if gatewayToken != cfg.RemoteGatewayToken {
		return http.StatusUnauthorized, errors.New("Pub gateway token is invalid")
	}

	jobInternalName := c.Request.Header.Get(JobInternalNameHeader)
	if jobInternalName == "" {
		return http.StatusBadRequest, errors.Errorf("Pub gateway expects job name in %s header", JobInternalNameHeader)
	}

	job := &JobDetails{
		Name:         jobName,
		Version:      jobVersion,
		InternalName: jobInternalName,
	}
	callerName := c.Request.Header.Get(cfg.CallerNameHeader)

	urlPath := JoinURL("/pub/job/", job.Name, job.Version, jobPath)
	targetUrl := TargetURL(cfg, job, urlPath)

	logger.Debug("Forwarding request to job", log.Ctx{
		"jobName":         jobName,
		"jobVersion":      jobVersion,
		"jobInternalName": jobInternalName,
		"targetUrl":       targetUrl.String(),
	})

	ServeReverseProxy(targetUrl, c, job, cfg, logger, requestId, callerName)
	return http.StatusOK, nil
}
