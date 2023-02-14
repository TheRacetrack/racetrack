package main

import (
	"fmt"
	"net/url"
	"path"
	"strings"
)

// Returns target proxy URL for job, which is accessed at urlPath
func TargetURL(cfg *Config, job *JobDetails, urlPath string) url.URL {
	return url.URL{
		Scheme: cfg.ForwardToProtocol,
		Host:   job.InternalName,
		Path:   urlPath,
	}
}

func JoinURL(base string, paths ...string) string {
	p := path.Join(paths...)
	return fmt.Sprintf("%s/%s", strings.TrimRight(base, "/"), strings.TrimLeft(p, "/"))
}
