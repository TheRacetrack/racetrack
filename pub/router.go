package main

import (
	"net/http"

	"github.com/gorilla/mux"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const baseIngressPath = "/pub"
const proxyPathTemplate = "/fatman/{fatman}/{version:[^/]+}{path:.*}"

func handlerWithConfig(fn func(http.ResponseWriter, *http.Request, *Config), cfg *Config) http.HandlerFunc {
	return func(res http.ResponseWriter, req *http.Request) {
		fn(res, req, cfg)
	}
}

func ListenAndServe(cfg *Config) error {
	router := mux.NewRouter()

	// Serve endpoints at raw path (when accessed internally, eg "/metrics")
	// and at prefixed path (when accessed through ingress proxy)
	baseUrls := []string{
		"",
		baseIngressPath,
	}
	for _, baseUrl := range baseUrls {
		router.HandleFunc(baseUrl+proxyPathTemplate, handlerWithConfig(proxyEndpoint, cfg))
		router.HandleFunc(baseUrl+"/live", handlerWithConfig(liveEndpoint, cfg))
		router.HandleFunc(baseUrl+"/ready", handlerWithConfig(readyEndpoint, cfg))
		router.HandleFunc(baseUrl+"/health", handlerWithConfig(healthEndpoint, cfg))
		router.Handle(baseUrl+"/metrics", promhttp.Handler())
	}

	listenAddress := "0.0.0.0:" + cfg.ListenPort
	log.Info("Listening on", log.Ctx{"listenAddress": listenAddress})
	if err := http.ListenAndServe(listenAddress, router); err != nil {
		log.Error("Serving http", log.Ctx{"error": err})
		return errors.Wrap(err, "Failed to serve")
	}
	return nil
}
