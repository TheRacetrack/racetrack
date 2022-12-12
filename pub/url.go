package main

import (
	"fmt"
	"net/url"
	"path"
	"strings"
)

// Returns target proxy URL for fatman, which is accessed at urlPath
func TargetURL(cfg *Config, fatman *FatmanDetails, urlPath string) url.URL {
	return url.URL{
		Scheme: cfg.ForwardToProtocol,
		Host:   fatman.InternalName,
		Path:   urlPath,
	}
}

func JoinURL(base string, paths ...string) string {
	p := path.Join(paths...)
	return fmt.Sprintf("%s/%s", strings.TrimRight(base, "/"), strings.TrimLeft(p, "/"))
}
