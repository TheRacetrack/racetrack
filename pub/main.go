package main

import (
	log "github.com/inconshreveable/log15"
)

func main() {
	ConfigureLog("debug", false)
	log.Info("Starting PUB")

	cfg, err := LoadConfig()
	if err != nil {
		panic(err)
	}
	ConfigureLog(cfg.LogLevel, cfg.StructuredLogging)

	err = ListenAndServe(cfg)
	if err != nil {
		panic(err)
	}
}
