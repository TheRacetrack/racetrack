package main

import (
	"fmt"
	"net/http"
	"os/exec"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

// A command called remotely by Racetrack host to manage infrastructure target
func remoteCommandEndpoint(c *gin.Context, cfg *Config) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})

	logger.Info("Incoming remote command", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleRemoteCommandRequest(c, cfg, logger, requestId)
	if err != nil {
		errorStr := err.Error()
		logger.Error("Remote command error", log.Ctx{
			"status": statusCode,
			"error":  errorStr,
			"path":   c.Request.URL.Path,
		})
		c.JSON(statusCode, gin.H{
			"error":     fmt.Sprintf("Remote command: %s", errorStr),
			"status":    http.StatusText(statusCode),
			"requestId": requestId,
		})
	}
}

type remoteCommandRequest struct {
	Command string `json:"command"`
	Workdir string `json:"workdir"`
}

func handleRemoteCommandRequest(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	requestId string,
) (int, error) {
	gatewayToken := c.Request.Header.Get(RemoteGatewayTokenHeader)
	if gatewayToken == "" {
		return http.StatusUnauthorized, errors.Errorf("remote Pub expects token in %s header", RemoteGatewayTokenHeader)
	}
	if gatewayToken != cfg.RemoteGatewayToken {
		return http.StatusUnauthorized, errors.New("remote Pub token is invalid")
	}

	var request remoteCommandRequest
	err := c.BindJSON(&request)
	if err != nil {
		return http.StatusBadRequest, errors.Wrap(err, "failed to parse request data as JSON")
	}
	if request.Command == "" {
		return http.StatusBadRequest, errors.New("command field is empty")
	}

	logger.Debug("Executing remote command", log.Ctx{
		"command": request.Command,
	})
	cmd := exec.Command("sh", "-c", request.Command)
	if request.Workdir != "" {
		cmd.Dir = request.Workdir
	}
	output, err := cmd.CombinedOutput()
	if err != nil {
		logger.Error("Command failed", log.Ctx{
			"command":   request.Command,
			"exit_code": cmd.ProcessState.ExitCode(),
			"err":       err,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"output":    string(output),
		"exit_code": cmd.ProcessState.ExitCode(),
		"requestId": requestId,
	})
	return http.StatusOK, nil
}
