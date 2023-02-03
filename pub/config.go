package main

import (
	"github.com/caarlos0/env"
	log "github.com/inconshreveable/log15"
)

type Config struct {
	LogLevel              string `env:"LOG_LEVEL" envDefault:"debug"`
	ListenPort            string `env:"PUB_PORT" envDefault:"7205"`
	ForwardToProtocol     string `env:"FORWARD_TO_PROTOCOL" envDefault:"http"`
	GitVersion            string `env:"GIT_VERSION"`
	LifecycleUrl          string `env:"LIFECYCLE_URL" envDefault:"http://localhost:7202/lifecycle"`
	AuthRequired          bool   `env:"AUTH_REQUIRED" envDefault:"false"`
	AuthDebug             bool   `env:"AUTH_DEBUG" envDefault:"false"`
	LifecycleToken        string `env:"LIFECYCLE_AUTH_TOKEN"` // Used to authenticate to Lifecycle for User endpoints
	RequestTracingHeader  string `env:"REQUEST_TRACING_HEADER" envDefault:"X-Request-Tracing-Id"`
	OpenTelemetryEndpoint string `env:"OPENTELEMETRY_ENDPOINT" envDefault:""`
}

func LoadConfig() (*Config, error) {
	var cfg Config
	if err := env.Parse(&cfg); err != nil {
		log.Error("Parsing config", log.Ctx{"error": err, "config": cfg})
		return nil, err
	}
	log.Debug("Config values", log.Ctx{"config": cfg})

	if !cfg.AuthRequired {
		log.Warn("Authentication is not required")
	}
	return &cfg, nil
}
