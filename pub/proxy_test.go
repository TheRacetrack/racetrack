package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	"github.com/stretchr/testify/assert"
)

func TestServeReverseProxy(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/pub/job/adder/0.0.1/api/v1/perform", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		w.WriteHeader(http.StatusOK)
		_, _ = io.WriteString(w, "hello from "+r.URL.Path)
	})

	mux.HandleFunc("/pub/job/adder/0.0.1/redirect-me", func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, "http://"+r.Host+"/pub/job/adder/0.0.1/api/v1/perform", http.StatusFound)
	})

	job := httptest.NewServer(mux)
	defer job.Close()

	jobURL, err := url.Parse(job.URL)
	assert.NoError(t, err)

	cfg := &Config{
		ForwardToProtocol:    "http",
		RequestTracingHeader: "X-Request-Tracing-Id",
		CallerNameHeader:     "X-Caller-Name",
	}
	jobDetails := &JobDetails{
		Name:         "adder",
		Version:      "0.0.1",
		InternalName: jobURL.Host,
	}

	router := gin.New()
	router.Any("/pub/job/:job/:version/*path", func(c *gin.Context) {
		isCallingLatest := c.Param("version") == "latest"
		target := url.URL{
			Scheme: jobURL.Scheme,
			Host:   jobURL.Host,
			Path:   "/pub/job/" + jobDetails.Name + "/" + jobDetails.Version + c.Param("path"),
		}
		ServeReverseProxy(target, c, jobDetails, cfg, log.New(), "trace-123", "bob", time.Now(), isCallingLatest)
	})
	server := httptest.NewServer(router)
	defer server.Close()

	res, err := http.Get(server.URL + "/pub/job/adder/latest/api/v1/perform")
	assert.NoError(t, err)
	body, err := io.ReadAll(res.Body)
	assert.NoError(t, err)
	res.Body.Close()

	assert.Equal(t, http.StatusOK, res.StatusCode)
	assert.Equal(t, "hello from /pub/job/adder/0.0.1/api/v1/perform", string(body))
	assert.Equal(t, "trace-123", res.Header.Get("X-Request-Tracing-Id"))
	

	// stop redirect to check where it redirects to
	client := &http.Client{
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse
		},
	}
	res, err = client.Get(server.URL + "/pub/job/adder/latest/redirect-me")
	assert.NoError(t, err)
	res.Body.Close()

	assert.Equal(t, http.StatusFound, res.StatusCode)
	assert.Equal(t, "/pub/job/adder/latest/api/v1/perform", res.Header.Get("Location"))
	
}
