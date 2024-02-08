package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
	uuid "github.com/satori/go.uuid"
)

type AsyncTaskStore struct {
	tasks            map[string]*AsyncTask
	httpClient       *http.Client
	rwMutex          sync.RWMutex
	longPollTimeout  time.Duration
	replicaDiscovery *replicaDiscovery
}

type AsyncTask struct {
	id               string
	status           TaskStatus
	jobName          string
	jobVersion       string
	jobPath          string
	httpMethod       string
	startedAt        time.Time
	endedAt          *time.Time
	resultData       []byte
	resultHeaders    map[string]string
	resultStatusCode *int
	result           interface{}
	errorMessage     *string
	doneChannel      chan string // channel to notify when task is done
}

type TaskStatus string

const (
	Ongoing   TaskStatus = "ongoing"
	Completed TaskStatus = "completed"
	Failed    TaskStatus = "failed"
)

func NewAsyncTaskStore(cfg *Config) *AsyncTaskStore {
	replicaDiscovery := NewReplicaDiscovery(cfg)
	return &AsyncTaskStore{
		tasks: make(map[string]*AsyncTask),
		httpClient: &http.Client{
			Timeout: 120 * time.Minute,
		},
		longPollTimeout:  30 * time.Second,
		replicaDiscovery: replicaDiscovery,
	}
}

// Start a new async job call in background and return task ID
func AsyncJobCallEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore, jobPath string) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})
	if strings.HasPrefix(jobPath, "//") {
		jobPath = jobPath[1:]
	}

	logger.Info("Request: new Async Job Call", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleAsyncJobCallRequest(c, cfg, taskStore, logger, requestId, jobPath)
	if err != nil {
		metricAsyncJobCallsErros.Inc()
		errorStr := err.Error()
		logger.Error("Async Job Call request error", log.Ctx{
			"status": statusCode,
			"error":  errorStr,
			"path":   c.Request.URL.Path,
		})
		c.JSON(statusCode, gin.H{
			"error":     fmt.Sprintf("Async Job Call request error: %s", errorStr),
			"requestId": requestId,
		})
	}
}

func handleAsyncJobCallRequest(
	c *gin.Context,
	cfg *Config,
	taskStore *AsyncTaskStore,
	logger log.Logger,
	requestId string,
	jobPath string,
) (int, error) {
	if c.Request.Method != "POST" && c.Request.Method != "GET" {
		c.Writer.Header().Set("Allow", "GET, POST")
		return http.StatusMethodNotAllowed, errors.New("Method not allowed")
	}
	jobName := c.Param("job")
	if jobName == "" {
		return http.StatusBadRequest, errors.New("Couldn't extract job name")
	}
	jobVersion := c.Param("version")
	if jobVersion == "" {
		return http.StatusBadRequest, errors.New("Couldn't extract job version")
	}

	job, _, callerName, statusCode, err := getAuthorizedJobDetails(c, cfg, requestId, jobName, jobVersion, jobPath)
	if err != nil {
		return statusCode, err
	}

	metricAsyncJobCallsStarted.WithLabelValues(job.Name, job.Version).Inc()

	urlPath := JoinURL("/pub/job/", job.Name, job.Version, jobPath)
	targetUrl := TargetURL(cfg, job, urlPath)

	task := &AsyncTask{
		id:          uuid.NewV4().String(),
		startedAt:   time.Now(),
		status:      Ongoing,
		jobName:     job.Name,
		jobVersion:  job.Version,
		jobPath:     jobPath,
		httpMethod:  c.Request.Method,
		doneChannel: make(chan string),
	}
	taskStore.rwMutex.Lock()
	taskStore.tasks[task.id] = task
	taskStore.rwMutex.Unlock()
	logger.Info("Async Job Call task created", log.Ctx{
		"taskId":     task.id,
		"jobName":    job.Name,
		"jobVersion": job.Version,
		"jobPath":    jobPath,
	})

	c.JSON(http.StatusCreated, gin.H{
		"task_id": task.id,
		"status":  task.status,
	})

	defer c.Request.Body.Close()
	requestBody, err := io.ReadAll(c.Request.Body)
	if err != nil {
		return http.StatusBadRequest, errors.Wrap(err, "failed to read request body")
	}

	go func() {
		err := makeAsyncJobCall(targetUrl, c, requestBody, job, cfg, logger, taskStore, task, requestId, callerName)

		task.endedAt = ptr(time.Now())
		if err == nil {
			task.status = Completed
			metricAsyncJobCallsDone.WithLabelValues(job.Name, job.Version).Inc()
		} else {
			task.status = Failed
			errorStr := err.Error()
			task.errorMessage = &errorStr
			logger.Error("Async Job Call request error", log.Ctx{
				"taskId":     task.id,
				"jobName":    job.Name,
				"jobVersion": job.Version,
				"jobStatus":  job.Status,
				"caller":     callerName,
				"host":       targetUrl.Host,
				"path":       targetUrl.Path,
				"error":      errorStr,
			})
			metricAsyncJobCallsErros.Inc()
		}

		// Notify subscribed listeners without blocking
		select {
		case task.doneChannel <- task.id:
		default:
		}
		close(task.doneChannel)
	}()

	return http.StatusOK, nil
}

func makeAsyncJobCall(
	target url.URL,
	c *gin.Context,
	requestBody []byte,
	job *JobDetails,
	cfg *Config,
	logger log.Logger,
	taskStore *AsyncTaskStore,
	task *AsyncTask,
	requestId string,
	callerName string,
) error {
	metricJobProxyRequestsStarted.WithLabelValues(job.Name, job.Version).Inc()
	jobCallStartTime := time.Now()

	requestBodyReader := bytes.NewReader(requestBody)
	req, err := http.NewRequest(c.Request.Method, target.String(), requestBodyReader)
	if err != nil {
		return errors.Wrap(err, "creating job request")
	}
	req.URL.Scheme = target.Scheme
	req.URL.Host = target.Host
	req.URL.Path = target.Path
	req.Header.Add("X-Forwarded-Host", req.Host)
	req.Host = target.Host
	req.Header.Set(cfg.RequestTracingHeader, requestId)
	if callerName != "" {
		req.Header.Set(cfg.CallerNameHeader, callerName)
	}
	req.RequestURI = ""
	res, err := taskStore.httpClient.Do(req)
	if err != nil {
		return errors.Wrap(err, "making request to a job")
	}

	// Transform redirect links to relative (without hostname).
	// Target server doesn't know it's being proxied so it tries to redirect to internal URL.
	location := res.Header.Get("Location")
	if location != "" {
		redirectUrl, err := url.Parse(location)
		if err == nil {
			redirectUrl.Host = ""
			redirectUrl.Scheme = ""
			res.Header.Set("Location", redirectUrl.String())
		}
	}
	res.Header.Set(cfg.RequestTracingHeader, requestId)

	task.resultStatusCode = ptr(res.StatusCode)
	defer res.Body.Close()
	bodyBytes, err := io.ReadAll(res.Body)
	if err != nil {
		return errors.Wrap(err, "failed to read response body")
	}
	task.resultData = bodyBytes
	task.resultHeaders = make(map[string]string)
	for k, v := range res.Header {
		task.resultHeaders[k] = strings.Join(v, ",")
	}
	contentType := res.Header.Get("Content-Type")
	if strings.Contains(contentType, "application/json") {
		err := json.Unmarshal(bodyBytes, &task.result)
		if err != nil {
			return errors.Wrap(err, "failed to parse response body as JSON")
		}
	}

	logger.Info("Async Job Call done", log.Ctx{
		"taskId":     task.id,
		"jobName":    job.Name,
		"jobVersion": job.Version,
		"jobPath":    target.Path,
		"caller":     callerName,
		"status":     res.StatusCode,
	})
	statusCode := strconv.Itoa(res.StatusCode)
	metricJobProxyResponseCodes.WithLabelValues(job.Name, job.Version, statusCode).Inc()
	jobCallTime := time.Since(jobCallStartTime).Seconds()
	metricJobCallResponseTimeHistogram.WithLabelValues(job.Name, job.Version).Observe(jobCallTime)
	metricJobCallResponseTime.WithLabelValues(job.Name, job.Version).Add(jobCallTime)
	metricJobProxyRequestsDone.WithLabelValues(job.Name, job.Version).Inc()
	return nil
}

func TaskExistEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore) {
	taskId := c.Param("taskId")
	taskStore.rwMutex.RLock()
	task, ok := taskStore.tasks[taskId]
	taskStore.rwMutex.RUnlock()
	if ok {
		c.JSON(http.StatusOK, gin.H{
			"task_id": task.id,
			"status":  task.status,
		})
	} else {
		c.JSON(http.StatusNotFound, gin.H{
			"error":     fmt.Sprintf("Task with id %s not found", taskId),
			"requestId": getRequestTracingId(c.Request, cfg.RequestTracingHeader),
		})
	}
}

// Wait using HTTP Long Polling until task is completed or timeout is reached
// Internal endpoint for communication between Pub replicas
// Ask single replica for task status without forwarding to other replicas
func SingleTaskPollEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore) {
	taskId := c.Param("taskId")
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})
	logger.Info("Request: Poll async task of this replica", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})

	taskStore.rwMutex.RLock()
	task, ok := taskStore.tasks[taskId]
	taskStore.rwMutex.RUnlock()
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{
			"error":     fmt.Sprintf("Task with id %s not found", taskId),
			"requestId": getRequestTracingId(c.Request, cfg.RequestTracingHeader),
		})
		return
	}

	if task.status != Ongoing {
		respondTaskResult(c, logger, task, taskStore)
		return
	}

	select {
	case _, ok := <-task.doneChannel: // channel notified or closed
		if !ok {
			break
		}
		break
	case <-c.Request.Context().Done():
		c.String(http.StatusGatewayTimeout, "Request canceled")
		return
	case <-time.After(taskStore.longPollTimeout):
		break
	}

	taskStore.rwMutex.RLock()
	task, ok = taskStore.tasks[taskId]
	taskStore.rwMutex.RUnlock()
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{
			"error": fmt.Sprintf("Task with id %s not found", taskId),
		})
		return
	}
	if task.status == Ongoing {
		c.String(http.StatusRequestTimeout, "Time out")
		return
	} else {
		respondTaskResult(c, logger, task, taskStore)
	}
}

// Wait using HTTP Long Polling until task is completed or timeout is reached
// If task is unrecognized, check it in other Pub replicas and forward the request to the one that has it
func TaskPollEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore) {
	taskId := c.Param("taskId")
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})
	logger.Info("Request: Poll async task", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})

	taskStore.rwMutex.RLock()
	_, ok := taskStore.tasks[taskId]
	taskStore.rwMutex.RUnlock()
	if ok {
		SingleTaskPollEndpoint(c, cfg, taskStore)
	} else {
		if len(taskStore.replicaDiscovery.otherReplicaIPs) > 0 {
			logger.Info("Checking unknown task in other replicas", log.Ctx{
				"taskId":          taskId,
				"otherReplicaIPs": taskStore.replicaDiscovery.otherReplicaIPs,
			})
			otherReplicaIPs := taskStore.replicaDiscovery.otherReplicaIPs
			foundOnReplicas := make(chan string)
			for _, replicaIp := range otherReplicaIPs {
				go func(replicaIp string) {
					exists, err := taskExistsInReplica(c, cfg, taskStore, replicaIp, taskId)
					if err != nil {
						logger.Error("Failed to check task on other Pub replica", log.Ctx{
							"error":     err,
							"taskId":    taskId,
							"replicaIp": replicaIp,
						})
						foundOnReplicas <- ""
						return
					}
					if exists {
						foundOnReplicas <- replicaIp
					} else {
						foundOnReplicas <- ""
					}
				}(replicaIp)
			}
			for range otherReplicaIPs {
				replicaIp := <-foundOnReplicas
				if replicaIp != "" {
					forwardTaskPollToReplica(c, cfg, logger, taskStore, replicaIp, taskId)
					return
				}
			}
		}

		c.JSON(http.StatusNotFound, gin.H{
			"error":     fmt.Sprintf("Task with id %s not found", taskId),
			"requestId": getRequestTracingId(c.Request, cfg.RequestTracingHeader),
		})
	}
}

func taskExistsInReplica(
	c *gin.Context,
	cfg *Config,
	taskStore *AsyncTaskStore,
	replicaIp string,
	taskId string,
) (bool, error) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})
	logger.Info("Request: Task existsence check", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})

	url := fmt.Sprintf("http://%s:%s/pub/async/task/%s/exist", replicaIp, cfg.ListenPort, taskId)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return false, errors.Wrap(err, "failed to create request to Pub replica")
	}
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		return false, errors.Wrap(err, "failed to make request to Pub replica")
	} else if res.StatusCode == http.StatusNotFound {
		return false, nil
	} else if res.StatusCode == http.StatusOK {
		return true, nil
	} else {
		return false, errors.Errorf("Response error when checking task on other Pub replica: %s", res.Status)
	}
}

func forwardTaskPollToReplica(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	taskStore *AsyncTaskStore,
	replicaIp string,
	taskId string,
) {
	logger.Info("Forwarding async task poll to other replica", log.Ctx{
		"taskId":    taskId,
		"replicaIp": replicaIp,
	})
	url := fmt.Sprintf("http://%s:%s/pub/async/task/%s/poll/single", replicaIp, cfg.ListenPort, taskId)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		logger.Error("Failed to make request to Pub replica", log.Ctx{
			"error": err,
			"url":   url,
		})
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":     "Failed to make request to Pub replica",
			"requestId": getRequestTracingId(c.Request, cfg.RequestTracingHeader),
		})
		return
	}
	res, err := taskStore.httpClient.Do(req)
	if err != nil {
		logger.Error("Failed to make request to Pub replica", log.Ctx{
			"error": err,
			"url":   url,
		})
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":     "Failed to make request to Pub replica",
			"requestId": getRequestTracingId(c.Request, cfg.RequestTracingHeader),
		})
		return
	}

	for k, v := range res.Header {
		c.Writer.Header()[k] = v
	}

	defer res.Body.Close()
	bodyBytes, err := io.ReadAll(res.Body)
	if err != nil {
		logger.Error("Failed to read response body", log.Ctx{
			"error": err,
		})
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":     errors.Wrap(err, "failed to read response body").Error(),
			"requestId": getRequestTracingId(c.Request, cfg.RequestTracingHeader),
		})
	}

	c.Data(res.StatusCode, res.Header.Get("Content-Type"), bodyBytes)
}

func respondTaskResult(c *gin.Context, logger log.Logger, task *AsyncTask, taskStore *AsyncTaskStore) {
	if task.status == Ongoing || task.status == Failed {
		var durationStr *string
		if task.endedAt != nil {
			duration := task.endedAt.Sub(task.startedAt).String()
			durationStr = &duration
		}
		var statusCode int = http.StatusOK
		if task.status == Failed {
			statusCode = http.StatusInternalServerError
		} else if task.status == Ongoing {
			statusCode = http.StatusAccepted
		}
		c.JSON(statusCode, gin.H{
			"task_id":     task.id,
			"status":      task.status,
			"job_name":    task.jobName,
			"job_version": task.jobVersion,
			"job_path":    task.jobPath,
			"http_method": task.httpMethod,
			"started_at":  task.startedAt,
			"ended_at":    task.endedAt,
			"duration":    durationStr,
			"error":       task.errorMessage,
		})
	} else if task.status == Completed {
		for k, v := range task.resultHeaders {
			c.Writer.Header().Set(k, v)
		}
		contentType, ok := task.resultHeaders["Content-Type"]
		if ok {
			c.Data(*task.resultStatusCode, contentType, task.resultData)
		} else {
			c.Data(*task.resultStatusCode, "", task.resultData)
		}
	}

	if task.status == Completed || task.status == Failed {
		go func() {
			// Delete task after short time in case of timeout occured while sending the result to the client
			time.Sleep(5 * time.Second)
			taskStore.rwMutex.Lock()
			delete(taskStore.tasks, task.id)
			taskStore.rwMutex.Unlock()
			logger.Info("Retrieved task has been deleted", log.Ctx{
				"taskId": task.id,
				"status": task.status,
			})
		}()
	}
}
