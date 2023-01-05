package main

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestFatmanPathExtraction(t *testing.T) {
	router := gin.Default()
	router.GET(baseIngressPath + "/fatman/:fatman/:version/*path", func(c *gin.Context) {
		fatman_name := c.Param("fatman")
		fatman_version := c.Param("version")
		fatman_path := c.Param("path")
		c.JSON(http.StatusOK, gin.H{
			"name": fatman_name,
			"path": fatman_path,
			"version": fatman_version,
		})
	})
	router.GET(baseIngressPath + "/fatman/:fatman/:version", func(c *gin.Context) {
		fatman_name := c.Param("fatman")
		fatman_version := c.Param("version")
		fatman_path := c.Param("path")
		c.JSON(http.StatusOK, gin.H{
			"name": fatman_name,
			"path": fatman_path,
			"version": fatman_version,
		})
	})

	{
		w := httptest.NewRecorder()
		req, _ := http.NewRequest(http.MethodGet, "/pub/fatman/name-123/latest/api/v1/perform", nil)
		router.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)
		assert.Equal(t, "{\"name\":\"name-123\",\"path\":\"/api/v1/perform\",\"version\":\"latest\"}", w.Body.String())
	}

	{
		w := httptest.NewRecorder()
		req, _ := http.NewRequest(http.MethodGet, "/pub/fatman/name-123/0.0.1/", nil)
		router.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)
		assert.Equal(t, "{\"name\":\"name-123\",\"path\":\"/\",\"version\":\"0.0.1\"}", w.Body.String())
	}

	{
		w := httptest.NewRecorder()
		req, _ := http.NewRequest(http.MethodGet, "/pub/fatman/name-123/0.0.2", nil)
		router.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)
		assert.Equal(t, "{\"name\":\"name-123\",\"path\":\"\",\"version\":\"0.0.2\"}", w.Body.String())
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
