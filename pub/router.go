package main

import (
	"context"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

func ListenAndServe(cfg *Config) error {
	gin.SetMode(gin.ReleaseMode) // Hide Debug Routings
	router := gin.New()
	router.Use(gin.Recovery())

	asyncTaskStore := NewAsyncTaskStore(cfg)

	// Serve endpoints at raw path (when accessed internally, eg "/metrics")
	// and at prefixed path (when accessed through ingress proxy)
	baseUrls := []string{
		"",
		fmt.Sprintf("/%s", cfg.ServiceName),
	}
	for _, baseUrl := range baseUrls {
		// Backwards compatability endpoints
		router.Any(baseUrl+"/fatman/:job/:version/*path", func(c *gin.Context) {
			proxyEndpoint(c, cfg, "/"+c.Param("path"))
		})
		router.Any(baseUrl+"/fatman/:job/:version", func(c *gin.Context) {
			proxyEndpoint(c, cfg, "")
		})

		router.Any(baseUrl+"/job/:job/:version/*path", func(c *gin.Context) {
			proxyEndpoint(c, cfg, "/"+c.Param("path"))
		})
		router.Any(baseUrl+"/job/:job/:version", func(c *gin.Context) {
			proxyEndpoint(c, cfg, "")
		})

		router.Any(baseUrl+"/async/new/job/:job/:version/*path", func(c *gin.Context) {
			AsyncJobCallEndpoint(c, cfg, asyncTaskStore, "/"+c.Param("path"))
		})
		router.Any(baseUrl+"/async/new/job/:job/:version", func(c *gin.Context) {
			AsyncJobCallEndpoint(c, cfg, asyncTaskStore, "")
		})
		router.GET(baseUrl+"/async/task/:taskId", func(c *gin.Context) {
			TaskStatusEndpoint(c, cfg, asyncTaskStore)
		})
		router.GET(baseUrl+"/async/task/:taskId/poll", func(c *gin.Context) {
			TaskPollEndpoint(c, cfg, asyncTaskStore)
		})
		router.GET(baseUrl+"/async/task/:taskId/poll/internal", func(c *gin.Context) {
			InternalTaskPollEndpoint(c, cfg, asyncTaskStore)
		})
		router.GET(baseUrl+"/async/task/:taskId/exist", func(c *gin.Context) {
			TaskExistEndpoint(c, cfg, asyncTaskStore)
		})

		router.Any(baseUrl+"/remote/forward/:job/:version/*path", func(c *gin.Context) {
			remoteForwardEndpoint(c, cfg, "/"+c.Param("path"))
		})
		router.Any(baseUrl+"/remote/forward/:job/:version", func(c *gin.Context) {
			remoteForwardEndpoint(c, cfg, "")
		})
		router.POST(baseUrl+"/remote/command", func(c *gin.Context) {
			remoteCommandEndpoint(c, cfg)
		})

		router.GET(baseUrl+"/live", liveEndpoint)
		router.GET(baseUrl+"/ready", readyEndpoint)
		router.GET(baseUrl+"/health", handlerWithConfig(healthEndpoint, cfg))

		router.GET(baseUrl+"/metrics", wrapHandler(promhttp.Handler()))
	}

	if cfg.RemoteGatewayMode {
		initRemoteGateway(router, cfg)
	}

	if cfg.OpenTelemetryEndpoint != "" {
		tp, err := SetupOpenTelemetry(router, cfg)
		if err != nil {
			return errors.Wrap(err, "Failed to setup OpenTelemetry")
		}
		defer func() {
			if err := tp.Shutdown(context.Background()); err != nil {
				log.Error("Shutting down OpenTelemetry", log.Ctx{"error": err})
			}
		}()
	}

	listenAddress := "0.0.0.0:" + cfg.ListenPort
	log.Info("Listening on", log.Ctx{"listenAddress": listenAddress})
	if err := router.Run(listenAddress); err != nil {
		log.Error("Serving http", log.Ctx{"error": err})
		return errors.Wrap(err, "Failed to serve")
	}
	return nil
}

func handlerWithConfig(fn func(http.ResponseWriter, *http.Request, *Config), cfg *Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		fn(c.Writer, c.Request, cfg)
	}
}

func wrapHandler(h http.Handler) gin.HandlerFunc {
	return func(c *gin.Context) {
		h.ServeHTTP(c.Writer, c.Request)
	}
}
