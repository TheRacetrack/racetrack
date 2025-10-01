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

// Builds URL by joining paths, leaving optional trailing slash as it is
func JoinURL(base string, paths ...string) string {
	p := path.Join(paths...)
	url := fmt.Sprintf("%s/%s", strings.TrimRight(base, "/"), strings.TrimLeft(p, "/"))
	last := paths[len(paths)-1]
	if strings.HasSuffix(last, "/") {
		return url + "/"
	} else {
		return url
	}
}
