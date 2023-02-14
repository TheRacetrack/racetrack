package main

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestJobPathExtraction(t *testing.T) {
	router := gin.Default()
	router.GET(baseIngressPath + "/job/:job/:version/*path", func(c *gin.Context) {
		job_name := c.Param("job")
		job_version := c.Param("version")
		job_path := c.Param("path")
		c.JSON(http.StatusOK, gin.H{
			"name": job_name,
			"path": job_path,
			"version": job_version,
		})
	})
	router.GET(baseIngressPath + "/job/:job/:version", func(c *gin.Context) {
		job_name := c.Param("job")
		job_version := c.Param("version")
		job_path := c.Param("path")
		c.JSON(http.StatusOK, gin.H{
			"name": job_name,
			"path": job_path,
			"version": job_version,
		})
	})

	{
		w := httptest.NewRecorder()
		req, _ := http.NewRequest(http.MethodGet, "/pub/job/name-123/latest/api/v1/perform", nil)
		router.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)
		assert.Equal(t, "{\"name\":\"name-123\",\"path\":\"/api/v1/perform\",\"version\":\"latest\"}", w.Body.String())
	}

	{
		w := httptest.NewRecorder()
		req, _ := http.NewRequest(http.MethodGet, "/pub/job/name-123/0.0.1/", nil)
		router.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)
		assert.Equal(t, "{\"name\":\"name-123\",\"path\":\"/\",\"version\":\"0.0.1\"}", w.Body.String())
	}

	{
		w := httptest.NewRecorder()
		req, _ := http.NewRequest(http.MethodGet, "/pub/job/name-123/0.0.2", nil)
		router.ServeHTTP(w, req)
		assert.Equal(t, http.StatusOK, w.Code)
		assert.Equal(t, "{\"name\":\"name-123\",\"path\":\"\",\"version\":\"0.0.2\"}", w.Body.String())
	}
}

func TestTargetURL(t *testing.T) {
	{
		job := &JobDetails{
			Name:         "svc-name",
			InternalName: "job-svc-name.racetrack.svc:1234",
		}
		cfg := Config{
			ForwardToProtocol: "http",
		}
		res := TargetURL(&cfg, job, "pub/job/golang/latest/api/v1/perform")
		assert.Equal(t, "http://job-svc-name.racetrack.svc:1234/pub/job/golang/latest/api/v1/perform", res.String())
	}

	{
		job := &JobDetails{
			Name:         "golang",
			InternalName: "job-golang:7000",
		}
		cfg := Config{
			ForwardToProtocol: "http",
		}
		res := TargetURL(&cfg, job, "/pub/job/golang/latest/api/v1/parameters")
		assert.Equal(t, "http://job-golang:7000/pub/job/golang/latest/api/v1/parameters", res.String())
	}
}

func TestJoinURL(t *testing.T) {
	base := "http://localhost:7002/lifecycle"
	url := JoinURL(base, "/api/v1/escs/", "1")
	assert.Equal(t, "http://localhost:7002/lifecycle/api/v1/escs/1", url)
}
