package main

import (
	"encoding/json"
	"net/http"

	log "github.com/inconshreveable/log15"
)

type HealthResponse struct {
	Service      string `json:"service"`
	Version      string `json:"version"`
	Status       string `json:"status"`
	AuthRequired bool   `json:"auth_required"`
}

func healthEndpoint(res http.ResponseWriter, req *http.Request, cfg *Config) {
	metricHealthRequests.Inc()
	health := HealthResponse{
		Service:      "pub",
		Version:      cfg.GitVersion,
		Status:       "pass",
		AuthRequired: cfg.AuthRequired,
	}

	res.Header().Set("Content-Type", "application/json")
	response, err := json.Marshal(&health)
	if err != nil {
		log.Error("Couldn't marshal json", log.Ctx{"error": err})
		res.Write([]byte("{\"status\": \"warn\"}"))
		return
	}
	res.Write(response)
}

func liveEndpoint(res http.ResponseWriter, req *http.Request, cfg *Config) {
	res.Header().Set("Content-Type", "application/json")
	res.Write([]byte("{\"live\": true}"))
}

func readyEndpoint(res http.ResponseWriter, req *http.Request, cfg *Config) {
	res.Header().Set("Content-Type", "application/json")
	res.Write([]byte("{\"ready\": true}"))
}
