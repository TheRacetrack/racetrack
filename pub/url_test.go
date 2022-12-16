package main

import (
	"net/http"
	"net/url"
	"testing"

	"github.com/gorilla/mux"
	"github.com/stretchr/testify/assert"
)

func TestFatmanPathExtraction(t *testing.T) {
	router := mux.NewRouter()
	router.NewRoute().Path(baseIngressPath + proxyPathTemplate)
	routeMatch := mux.RouteMatch{}

	{
		request := http.Request{Method: "GET", URL: &url.URL{Path: "/pub/fatman/name-123/latest/api/v1/perform"}}
		assert.True(t, router.Match(&request, &routeMatch))
		assert.Equal(t, "name-123", routeMatch.Vars["fatman"])
		assert.Equal(t, "latest", routeMatch.Vars["version"])
		assert.Equal(t, "/api/v1/perform", routeMatch.Vars["path"])
	}

	{
		request := http.Request{Method: "GET", URL: &url.URL{Path: "/pub/fatman/name-123/0.0.1/"}}
		assert.True(t, router.Match(&request, &routeMatch))
		assert.Equal(t, "name-123", routeMatch.Vars["fatman"])
		assert.Equal(t, "0.0.1", routeMatch.Vars["version"])
		assert.Equal(t, "/", routeMatch.Vars["path"])
	}

	{
		request := http.Request{Method: "GET", URL: &url.URL{Path: "/pub/fatman/name-123/0.0.2"}}
		assert.True(t, router.Match(&request, &routeMatch))
		assert.Equal(t, "name-123", routeMatch.Vars["fatman"])
		assert.Equal(t, "0.0.2", routeMatch.Vars["version"])
		assert.Equal(t, "", routeMatch.Vars["path"])
	}
}

func TestTargetURL(t *testing.T) {
	{
		fatman := &FatmanDetails{
			Name:         "svc-name",
			InternalName: "fatman-svc-name.racetrack.svc:1234",
		}
		cfg := Config{
			ForwardToProtocol: "http",
		}
		res := TargetURL(&cfg, fatman, "pub/fatman/golang/latest/api/v1/perform")
		assert.Equal(t, "http://fatman-svc-name.racetrack.svc:1234/pub/fatman/golang/latest/api/v1/perform", res.String())
	}

	{
		fatman := &FatmanDetails{
			Name:         "golang",
			InternalName: "fatman-golang:7000",
		}
		cfg := Config{
			ForwardToProtocol: "http",
		}
		res := TargetURL(&cfg, fatman, "/pub/fatman/golang/latest/api/v1/parameters")
		assert.Equal(t, "http://fatman-golang:7000/pub/fatman/golang/latest/api/v1/parameters", res.String())
	}
}

func TestJoinURL(t *testing.T) {
	base := "http://localhost:7002/lifecycle"
	url := JoinURL(base, "/api/v1/escs/", "1")
	assert.Equal(t, "http://localhost:7002/lifecycle/api/v1/escs/1", url)
}
