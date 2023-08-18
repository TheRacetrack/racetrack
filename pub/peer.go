package main

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

const RemoteInfraTokenHeader = "X-Racetrack-Peer-Token"
const JobInternalNameHeader = "X-Racetrack-Job-Internal-Name"

func peerForwardEndpoint(c *gin.Context, cfg *Config) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})

	logger.Info("Incoming forwarding request from master PUB", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handlePeerForwardRequest(c, cfg, logger, requestId)
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

func handlePeerForwardRequest(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	requestId string,
) (int, error) {

	if !cfg.PeerMode {
		return http.StatusUnauthorized, errors.New("Forwarding endpoint is only available in peer mode")
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

	pubAuthToken := c.Request.Header.Get(RemoteInfraTokenHeader)
	if pubAuthToken == "" {
		return http.StatusUnauthorized, errors.Errorf("Peer PUB expects %s header", RemoteInfraTokenHeader)
	}
	if pubAuthToken != cfg.PeerAuthKey {
		return http.StatusUnauthorized, errors.New("Peer PUB token is invalid")
	}

	jobInternalName := c.Request.Header.Get(JobInternalNameHeader)

	job := &JobDetails{
		Name:         jobName,
		Version:      jobVersion,
		InternalName: jobInternalName,
	}
	callerName := c.Request.Header.Get(cfg.CallerNameHeader)

	targetUrl := TargetURL(cfg, job, c.Request.URL.Path)
	ServeReverseProxy(targetUrl, c, job, cfg, logger, requestId, callerName)
	return 200, nil
}
