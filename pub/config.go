package main

import (
	"github.com/caarlos0/env"
	log "github.com/inconshreveable/log15"
)

type Config struct {
	LogLevel                 string `env:"LOG_LEVEL" envDefault:"debug"`
	ListenPort               string `env:"PUB_PORT" envDefault:"7205"`
	ForwardToProtocol        string `env:"FORWARD_TO_PROTOCOL" envDefault:"http"`
	GitVersion               string `env:"GIT_VERSION"`
	LifecycleUrl             string `env:"LIFECYCLE_URL" envDefault:"http://127.0.0.1:7202/lifecycle"`
	AuthRequired             bool   `env:"AUTH_REQUIRED" envDefault:"true"`
	AuthDebug                bool   `env:"AUTH_DEBUG" envDefault:"false"`
	LifecycleToken           string `env:"LIFECYCLE_AUTH_TOKEN"` // Used to authenticate to Lifecycle for User endpoints
	RequestTracingHeader     string `env:"REQUEST_TRACING_HEADER" envDefault:"X-Request-Tracing-Id"`
	CallerNameHeader         string `env:"CALLER_NAME_HEADER" envDefault:"X-Caller-Name"`
	RemoteGatewayMode        bool   `env:"REMOTE_GATEWAY_MODE" envDefault:"false"`
	RemoteGatewayToken       string `env:"REMOTE_GATEWAY_TOKEN" envDefault:""`
	ServiceName              string `env:"SERVICE_NAME" envDefault:"pub"`
	StructuredLogging        bool   `env:"LOG_STRUCTURED" envDefault:"false"`
	ReplicaDiscoveryHostname string `env:"REPLICA_DISCOVERY_HOSTNAME" envDefault:""`
	AsyncMaxAttempts         int    `env:"ASYNC_MAX_ATTEMPTS" envDefault:"2"`         // Maximum number of attempts to make a job call (1 is no retry)
	AsyncTaskRetryInterval   int    `env:"ASYNC_TASK_RETRY_INTERVAL" envDefault:"10"` // Interval in seconds to wait before retrying a crashed job call
	LifecycleCacheTTLMin     int    `env:"LIFECYCLE_CACHE_TTL_MIN" envDefault:"60"`   // Time-to-live in seconds to keep cached Lifecycle responses
	LifecycleCacheTTLMax     int    `env:"LIFECYCLE_CACHE_TTL_MAX" envDefault:"600"`  // Time-to-live in seconds to keep cached Lifecycle responses in case of Lifecycle/Database outage
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
