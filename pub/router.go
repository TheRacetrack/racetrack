package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

func ListenAndServe(cfg *Config) error {
	gin.SetMode(gin.ReleaseMode) // Hide Debug Routings
	router := gin.New()
	router.Use(gin.CustomRecovery(recoverPanic))

	services := InitServices(cfg)

	// Serve endpoints at raw path (when accessed internally, eg "/metrics")
	// and at prefixed path (when accessed through ingress proxy)
	baseUrls := []string{"", fmt.Sprintf("/%s", cfg.ServiceName)}
	for _, baseUrl := range baseUrls {
		SetupEndpoints(router, cfg, baseUrl, services)
	}

	if cfg.RemoteGatewayMode {
		initRemoteGateway(router, cfg)
	}

	listenAddress := "0.0.0.0:" + cfg.ListenPort
	server := &http.Server{
		Addr:    listenAddress,
		Handler: router.Handler(),
	}
	go func() {
		quit := make(chan os.Signal, 1)
		signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
		sig := <-quit
		log.Info("Shutting down server...", log.Ctx{"signal": sig})
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		services.Shutdown()
		if err := server.Shutdown(ctx); err != nil {
			log.Error("Shutting down server", log.Ctx{"error": err})
		}
		<-ctx.Done()
		log.Info("Server shutdown timeout")
	}()
	log.Info("Listening on", log.Ctx{"listenAddress": listenAddress})
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Error("Serving http", log.Ctx{"error": err})
		return errors.Wrap(err, "Failed to serve")
	}
	log.Info("Server closed")
	return nil
}

func SetupEndpoints(
	router *gin.Engine,
	cfg *Config,
	baseUrl string,
	services *Services,
) {
	// Backwards compatability endpoints
	router.Any(baseUrl+"/fatman/:job/:version/*path", func(c *gin.Context) {
		proxyEndpoint(c, services, "/"+c.Param("path"))
	})
	router.Any(baseUrl+"/fatman/:job/:version", func(c *gin.Context) {
		proxyEndpoint(c, services, "")
	})

	router.Any(baseUrl+"/job/:job/:version/*path", func(c *gin.Context) {
		proxyEndpoint(c, services, "/"+c.Param("path"))
	})
	router.Any(baseUrl+"/job/:job/:version", func(c *gin.Context) {
		proxyEndpoint(c, services, "")
	})

	router.Any(baseUrl+"/async/new/job/:job/:version/*path", func(c *gin.Context) {
		TaskStartEndpoint(c, services, "/"+c.Param("path"))
	})
	router.Any(baseUrl+"/async/new/job/:job/:version", func(c *gin.Context) {
		TaskStartEndpoint(c, services, "")
	})
	router.GET(baseUrl+"/async/task/:taskId/poll", func(c *gin.Context) {
		TaskPollEndpoint(c, cfg, services.asyncTaskStore)
	})
	router.GET(baseUrl+"/async/task/:taskId/poll/local", func(c *gin.Context) {
		LocalTaskPollEndpoint(c, cfg, services.asyncTaskStore, true)
	})
	router.GET(baseUrl+"/async/task/:taskId/status", func(c *gin.Context) {
		TaskStatusEndpoint(c, cfg, services.asyncTaskStore)
	})
	router.GET(baseUrl+"/async/task/:taskId/status/local", func(c *gin.Context) {
		LocalTaskStatusEndpoint(c, cfg, services.asyncTaskStore)
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

func recoverPanic(c *gin.Context, err any) {
	metricPanicErrors.Inc()
	var path string
	if c.Request != nil && c.Request.URL != nil {
		path = c.Request.URL.Path
	}
	log.Error("Panic error recovered", log.Ctx{
		"error": err,
		"path":  path,
	})
}
