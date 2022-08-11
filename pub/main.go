package main

import (
	log "github.com/inconshreveable/log15"
)

func main() {
	ConfigureLog("debug")
	log.Info("Starting PUB")

	cfg, err := LoadConfig()
	if err != nil {
		panic(err)
	}
	ConfigureLog(cfg.LogLevel)

	err = ListenAndServe(cfg)
	if err != nil {
		panic(err)
	}
}
