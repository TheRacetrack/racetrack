package main

import (
	"fmt"
	"net/url"
	"path"
	"strings"
)

// Returns target proxy URL for fatman, which is accessed at urlPath
func TargetURL(cfg *Config, fatman *FatmanDetails, urlPath string) url.URL {

	var host string
	// useful for tests when target domain is localhost
	if cfg.ForwardToDomain == "localhost" {
		host = fatman.InternalName
	} else {
		host = fmt.Sprintf("%s.%s:%s", fatman.InternalName, cfg.ForwardToDomain, cfg.ForwardToPort)
	}

	target := url.URL{
		Scheme: cfg.ForwardToProtocol,
		Host:   host,
		Path:   urlPath,
	}

	return target
}

func JoinURL(base string, paths ...string) string {
	p := path.Join(paths...)
	return fmt.Sprintf("%s/%s", strings.TrimRight(base, "/"), strings.TrimLeft(p, "/"))
}
