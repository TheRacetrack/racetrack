package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	uuid "github.com/satori/go.uuid"
)

// Start a new async job call in background and return task ID
func TaskStartEndpoint(c *gin.Context, services *Services, jobPath string) {
	cfg := services.config
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{"requestId": requestId})
	if strings.HasPrefix(jobPath, "//") {
		jobPath = jobPath[1:]
	}

	logger.Info("Request: new Async Job Call", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleTaskStartRequest(c, services, logger, requestId, jobPath)
	if err != nil {
		metricAsyncJobCallsErrors.Inc()
		respondError(c, cfg, logger, statusCode, "Async Job Call request error", err, map[string]any{
			"path": c.Request.URL.Path,
		})
	}
}

func handleTaskStartRequest(
	c *gin.Context,
	services *Services,
	logger log.Logger,
	requestId string,
	jobPath string,
) (int, error) {
	cfg := services.config
	taskStore := services.asyncTaskStore

	if c.Request.Method != "POST" && c.Request.Method != "GET" {
		c.Writer.Header().Set("Allow", "GET, POST")
		return http.StatusMethodNotAllowed, errors.New("method not allowed")
	}
	jobName := c.Param("job")
	if jobName == "" {
		return http.StatusBadRequest, errors.New("couldn't extract job name")
	}
	jobVersion := c.Param("version")
	if jobVersion == "" {
		return http.StatusBadRequest, errors.New("couldn't extract job version")
	}

	job, _, callerName, statusCode, err := getAuthorizedJobDetails(c, services, requestId, jobName, jobVersion, jobPath)
	if err != nil {
		return statusCode, err
	}

	metricAsyncJobCallsStarted.WithLabelValues(job.Name, job.Version).Inc()
	urlPath := JoinURL("/pub/job/", job.Name, job.Version, jobPath)
	targetUrl := TargetURL(cfg, job, urlPath)
	requestHeaders := make(map[string]string)
	for k, v := range c.Request.Header {
		requestHeaders[k] = strings.Join(v, ",")
	}
	requestHeaders[cfg.RequestTracingHeader] = requestId
	requestHeaders[cfg.CallerNameHeader] = callerName
	defer c.Request.Body.Close()
	requestBody, err := io.ReadAll(c.Request.Body)
	if err != nil {
		return http.StatusBadRequest, WrapError("failed to read request body", err)
	}

	task, err := taskStore.CreateTask(&AsyncTask{
		Id:                 uuid.NewV4().String(),
		Status:             Ongoing,
		StartedAtTimestamp: time.Now().Unix(),
		startedAt:          time.Now(),
		JobName:            job.Name,
		JobVersion:         job.Version,
		JobPath:            jobPath,
		RequestMethod:      c.Request.Method,
		RequestUrl:         c.Request.URL.String(),
		RequestHeaders:     requestHeaders,
		RequestBody:        string(requestBody),
		Attempts:           1,
		PubInstanceAddr:    taskStore.replicaDiscovery.MyAddr,
		doneChannel:        make(chan string),
		quitChannel:        make(chan bool, 1),
	})
	if err != nil {
		return http.StatusInternalServerError, WrapError("failed to create async task", err)
	}
	logger = logger.New(log.Ctx{"taskId": task.Id})
	logger.Info("Async Job Call task created", log.Ctx{
		"jobName":    job.Name,
		"jobVersion": job.Version,
		"jobPath":    jobPath,
		"caller":     callerName,
	})
	c.JSON(http.StatusCreated, gin.H{ // 201 Created
		"task_id": task.Id,
		"status":  task.Status,
	})

	go handleBackgroundJobCall(cfg, taskStore, logger, job, task, targetUrl, requestBody, requestId)
	return http.StatusOK, nil
}

func handleBackgroundJobCall(
	cfg *Config,
	taskStore *AsyncTaskStore,
	logger log.Logger,
	job *JobDetails,
	task *AsyncTask,
	targetUrl url.URL,
	requestBody []byte,
	requestId string,
) {
	err, retriable := makeJobCall(targetUrl, requestBody, cfg, taskStore, task, requestId)

	taskCopy := *task
	taskCopy.endedAt = ptr(time.Now())
	taskCopy.EndedAtTimestamp = ptr(time.Now().Unix())
	if err == nil {
		taskCopy.Status = Completed
		taskCopy.ErrorMessage = nil
		taskCopy.RetriableError = false
		metricAsyncJobCallsDone.WithLabelValues(job.Name, job.Version).Inc()
		duration := taskCopy.endedAt.Sub(taskCopy.startedAt).String()
		logger.Info("Async Job Call task has ended successfully", log.Ctx{
			"jobName":    job.Name,
			"jobVersion": job.Version,
			"jobPath":    targetUrl.Path,
			"statusCode": *taskCopy.ResponseStatusCode,
			"duration":   duration,
		})
	} else {
		taskCopy.Status = Failed
		taskCopy.ErrorMessage = ptr(err.Error())
		taskCopy.RetriableError = retriable
		logger.Error("Async Job Call request error", log.Ctx{
			"jobName":    job.Name,
			"jobVersion": job.Version,
			"host":       targetUrl.Host,
			"path":       targetUrl.Path,
			"error":      err.Error(),
		})
		metricAsyncJobCallsErrors.Inc()
	}

	if taskCopy.canBeRetried(cfg) {
		logger.Info("Async job call crashed, retrying...")
		time.Sleep(time.Duration(cfg.AsyncTaskRetryInterval) * time.Second)
		metricAsyncRetriedCrashedTask.Inc()
		err = retryJobCall(cfg, taskStore, logger, &taskCopy, requestId)
		if err != nil {
			logger.Error("Failed to retry async task call", log.Ctx{
				"error": err.Error(),
			})
		}
		return
	}

	err = taskStore.UpdateTask(&taskCopy)
	if err != nil {
		logger.Error("Failed to update async task", log.Ctx{
			"error": err.Error(),
		})
	}

	select { // Notify subscribed listeners without blocking
	case taskCopy.doneChannel <- taskCopy.Id:
	default:
	}
	close(taskCopy.doneChannel)
}

// Make an HTTP request to the target Job and keep the result of the task
// Return error, boolean whether the error is retriable
func makeJobCall(
	target url.URL,
	requestBody []byte,
	cfg *Config,
	taskStore *AsyncTaskStore,
	task *AsyncTask,
	requestId string,
) (error, bool) {
	metricJobProxyRequestsStarted.WithLabelValues(task.JobName, task.JobVersion).Inc()
	jobCallStartTime := time.Now()

	requestBodyReader := bytes.NewReader(requestBody)
	req, err := http.NewRequest(task.RequestMethod, target.String(), requestBodyReader)
	if err != nil {
		return WrapError("creating job request", err), false
	}
	for k, v := range task.RequestHeaders {
		req.Header.Set(k, v)
	}
	req.URL.Scheme = target.Scheme
	req.URL.Host = target.Host
	req.URL.Path = target.Path
	req.Header.Set("X-Forwarded-Host", req.Host)
	req.Host = target.Host
	req.RequestURI = ""
	req.Close = true

	res, err := taskStore.jobHttpClient.Do(req)
	if err != nil {
		if errors.Is(err, io.EOF) {
			return WrapError("connection broken to a target job (job may have died)", err), true
		}
		if errors.Is(err, syscall.ECONNREFUSED) {
			return WrapError("connection refused to a target job (job may have died)", err), true
		}
		return WrapError("making request to a job", err), true
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

	task.ResponseStatusCode = ptr(res.StatusCode)
	defer res.Body.Close()
	bodyBytes, err := io.ReadAll(res.Body)
	if err != nil {
		return WrapError("failed to read response body", err), false
	}
	task.ResponseBody = string(bodyBytes)
	task.ResponseHeaders = make(map[string]string)
	for k, v := range res.Header {
		task.ResponseHeaders[k] = strings.Join(v, ",")
	}

	if res.StatusCode == http.StatusNotFound {
		return fmt.Errorf("job returned 404 Not Found response: %s", task.ResponseBody), true
	}

	statusCode := strconv.Itoa(res.StatusCode)
	metricJobProxyResponseCodes.WithLabelValues(task.JobName, task.JobVersion, statusCode).Inc()
	jobCallTime := time.Since(jobCallStartTime).Seconds()
	metricJobCallResponseTimeHistogram.WithLabelValues(task.JobName, task.JobVersion).Observe(jobCallTime)
	metricJobCallResponseTime.WithLabelValues(task.JobName, task.JobVersion).Add(jobCallTime)
	metricJobProxyRequestsDone.WithLabelValues(task.JobName, task.JobVersion).Inc()
	return nil, false
}

// Get status of a task in this local replica instance
func LocalTaskStatusEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore) {
	taskId := c.Param("taskId")
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{"requestId": requestId, "taskId": taskId})
	logger.Info("Request: local async task status")

	task, ok := taskStore.GetLocalTask(taskId)
	if ok {
		c.JSON(http.StatusOK, gin.H{
			"task_id": task.Id,
			"status":  task.Status,
		})
	} else {
		c.JSON(http.StatusNotFound, gin.H{
			"error":     fmt.Sprintf("Task with id %s not found", taskId),
			"requestId": getRequestTracingId(c.Request, cfg.RequestTracingHeader),
		})
	}
}

// Get status of an async task in all Pub instances.
// If a task is not found, check it in other Pub replicas
func TaskStatusEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore) {
	taskId := c.Param("taskId")
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{"requestId": requestId, "taskId": taskId})
	logger.Info("Request: async task status")

	storedTask, ok := taskStore.GetLocalTask(taskId)
	if ok {
		c.JSON(http.StatusOK, gin.H{
			"task_id": storedTask.Id,
			"status":  storedTask.Status,
		})
		return
	}

	storedTask, err := taskStore.GetStoredTask(taskId)
	if errors.Is(err, ErrAsyncTaskNotFound) {
		respondError(c, cfg, logger, http.StatusNotFound,
			"Task not found in Lifecycle", err, nil)
		return
	}
	if err != nil {
		respondError(c, cfg, logger, http.StatusInternalServerError,
			"Failed to check async task in task storage", err, nil)
		return
	}
	task := NewLocalTask(storedTask)

	_, err = retryTaskIfMissing(cfg, taskStore, logger, task, requestId)
	if err != nil {
		respondError(c, cfg, logger, http.StatusInternalServerError,
			"Failed to retry a missing async task", err, map[string]any{
				"pubInstance": task.PubInstanceAddr,
			})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"task_id": task.Id,
		"status":  task.Status,
	})
}

func checkTaskStatusInReplica(
	taskStore *AsyncTaskStore,
	replicaAddr string,
	taskId string,
) (bool, string, error) {
	url := fmt.Sprintf("http://%s/pub/async/task/%s/status/local", replicaAddr, taskId)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return false, "", WrapError("failed to create request to Pub replica", err)
	}
	res, err := taskStore.replicaHttpClient.Do(req)
	if err != nil {
		return false, "", WrapError("failed to make status request to Pub replica", err)
	} else if res.StatusCode == http.StatusNotFound {
		return false, "", nil
	} else if res.StatusCode == http.StatusOK {
		dto := &AsyncTaskStatusDto{}
		defer res.Body.Close()
		err = json.NewDecoder(res.Body).Decode(dto)
		if err != nil {
			return false, "", WrapError("failed to parse response body as JSON", err)
		}
		return true, string(dto.Status), nil
	} else {
		return false, "", fmt.Errorf("response error when checking task on other Pub replica: %s", res.Status)
	}
}

// Wait using HTTP Long Polling until task is completed or timeout is reached
// If task is unrecognized, check it in other Pub replicas and forward the request to the one that has it
func TaskPollEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore) {
	taskId := c.Param("taskId")
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{"requestId": requestId, "taskId": taskId})
	logger.Info("Request: Poll async task", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})

	_, ok := taskStore.GetLocalTask(taskId)
	if ok {
		LocalTaskPollEndpoint(c, cfg, taskStore, false)
	} else {
		storedTask, err := taskStore.GetStoredTask(taskId)
		if errors.Is(err, ErrAsyncTaskNotFound) {
			respondError(c, cfg, logger, http.StatusNotFound,
				"Task not found in Lifecycle", err, nil)
			return
		}
		if err != nil {
			respondError(c, cfg, logger, http.StatusInternalServerError,
				"Failed to look up the async task in Lifecycle", err, nil)
			return
		}
		task := NewLocalTask(storedTask)

		if task.Status != Ongoing {
			respondTaskResult(c, logger, task, taskStore)
			return
		}

		retried, err := retryTaskIfMissing(cfg, taskStore, logger, task, requestId)
		if err != nil {
			respondError(c, cfg, logger, http.StatusInternalServerError,
				"Failed to retry a missing async task", err, map[string]any{
					"pubInstance": task.PubInstanceAddr,
				})
			return
		}
		if retried {
			LocalTaskPollEndpoint(c, cfg, taskStore, false)
			return
		}

		forwardTaskPollToReplica(c, cfg, logger, taskStore, task.PubInstanceAddr, taskId)
	}
}

// Wait using HTTP Long Polling until task is completed or timeout is reached.
// It's an internal endpoint used for communication between Pub replicas.
// It checks the result locally and does not search in other replicas.
func LocalTaskPollEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore, accessLog bool) {
	taskId := c.Param("taskId")
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{"requestId": requestId, "taskId": taskId})
	if accessLog {
		logger.Info("Request: Polling local async task", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	}

	task, ok := taskStore.GetLocalTask(taskId)
	if !ok {
		respondError(c, cfg, logger, http.StatusNotFound,
			"Task not found locally", nil, nil)
		return
	}
	if task.Status != Ongoing {
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
	case <-task.quitChannel:
		c.String(http.StatusRequestTimeout, "Request time-out due to termination signal")
		return
	case <-time.After(taskStore.longPollTimeout):
		break
	}

	task, ok = taskStore.GetLocalTask(taskId)
	if !ok {
		logger.Warn("Task not found locally after time-out")
		c.String(http.StatusRequestTimeout, "Time-out")
		return
	}
	if task.Status == Ongoing {
		c.String(http.StatusRequestTimeout, "Time-out")
		return
	} else {
		respondTaskResult(c, logger, task, taskStore)
	}
}

func forwardTaskPollToReplica(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	taskStore *AsyncTaskStore,
	replicaAddr string,
	taskId string,
) {
	logger.Info("Forwarding async task poll to other replica", log.Ctx{
		"replicaAddr": replicaAddr,
	})
	url := fmt.Sprintf("http://%s/pub/async/task/%s/poll/local", replicaAddr, taskId)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		respondError(c, cfg, logger, http.StatusServiceUnavailable,
			"Failed to make request to Pub replica", err, map[string]any{
				"url": url,
			})
		return
	}
	res, err := taskStore.replicaPollHttpClient.Do(req)
	if err != nil {
		respondError(c, cfg, logger, http.StatusServiceUnavailable,
			"Failed to forward task poll request to Pub replica", err, map[string]any{
				"url": url,
			})
		return
	}

	for k, v := range res.Header {
		c.Writer.Header()[k] = v
	}
	defer res.Body.Close()
	bodyBytes, err := io.ReadAll(res.Body)
	if err != nil {
		respondError(c, cfg, logger, http.StatusServiceUnavailable,
			"Failed to read response body", err, nil)
		return
	}
	c.Data(res.StatusCode, res.Header.Get("Content-Type"), bodyBytes)
}

func (task *AsyncTask) canBeRetried(cfg *Config) bool {
	return task.Attempts < cfg.AsyncMaxAttempts && task.Status == Failed && task.RetriableError
}

func retryJobCall(
	cfg *Config,
	taskStore *AsyncTaskStore,
	logger log.Logger,
	task *AsyncTask,
	requestId string,
) error {
	task.Attempts++
	task.PubInstanceAddr = taskStore.replicaDiscovery.MyAddr
	task.Status = Ongoing
	metricAsyncRetriedTask.Inc()
	errorMessage := ""
	if task.ErrorMessage != nil {
		errorMessage = *task.ErrorMessage
	}
	logger.Info("Retrying async job call", log.Ctx{
		"jobName":      task.JobName,
		"jobVersion":   task.JobVersion,
		"jobPath":      task.JobPath,
		"attempts":     task.Attempts,
		"replicaAddr":  task.PubInstanceAddr,
		"errorMessage": errorMessage,
	})
	job, jobDetailsErr := getJobDetails(cfg, task.JobName, task.JobVersion)
	if jobDetailsErr != nil {
		logger.Error("failed to get job details", log.Ctx{
			"error": jobDetailsErr.Error(),
		})
		task.Status = Failed
		task.ErrorMessage = ptr(jobDetailsErr.Error())
	}
	err := taskStore.UpdateTask(task)
	if err != nil {
		logger.Error("Failed to update async task", log.Ctx{
			"error": err.Error(),
		})
	}
	if jobDetailsErr != nil {
		return WrapError("failed to get job details", err)
	}

	urlPath := JoinURL("/pub/job/", task.JobName, task.JobVersion, task.JobPath)
	targetUrl := TargetURL(cfg, job, urlPath)
	requestBody := []byte(task.RequestBody)

	go handleBackgroundJobCall(cfg, taskStore, logger, job, task, targetUrl, requestBody, requestId)
	return nil
}

// Ensure task is retried if it's supposed to be running but is missing
func retryTaskIfMissing(
	cfg *Config,
	taskStore *AsyncTaskStore,
	logger log.Logger,
	task *AsyncTask,
	requestId string,
) (bool, error) {
	if task.Status != Ongoing {
		return false, nil // completed or failed task doesn't need to be retried
	}
	if !isTaskMissing(cfg, taskStore, task) {
		return false, nil
	}
	logger.Info("Task is gone in a supposed Pub replica, retrying missing task", log.Ctx{
		"pubInstance": task.PubInstanceAddr,
	})
	metricAsyncRetriedMissingTask.Inc()
	err := retryJobCall(cfg, taskStore, logger, task, requestId)
	if err != nil {
		return false, WrapError("failed to retry a job call", err)
	}
	return true, nil
}

func isTaskMissing(cfg *Config, taskStore *AsyncTaskStore, task *AsyncTask) bool {
	if task.PubInstanceAddr != "" && task.PubInstanceAddr == taskStore.replicaDiscovery.MyAddr {
		return true
	}
	if task.PubInstanceAddr == "" {
		task.PubInstanceAddr = fmt.Sprintf("127.0.0.1:%s", cfg.ListenPort)
	}
	exists, status, err := checkTaskStatusInReplica(taskStore, task.PubInstanceAddr, task.Id)
	if err != nil {
		return true // Failed to check async task in a supposed Pub replica
	}
	if !exists {
		return true // Task not found in a supposed replica
	}
	task.Status = TaskStatus(status)
	return false
}

func respondTaskResult(c *gin.Context, logger log.Logger, task *AsyncTask, taskStore *AsyncTaskStore) {
	if task.Status == Ongoing || task.Status == Failed {
		var durationStr *string
		if task.endedAt != nil {
			duration := task.endedAt.Sub(task.startedAt).String()
			durationStr = &duration
		}
		var statusCode int = http.StatusOK
		if task.Status == Failed {
			statusCode = http.StatusInternalServerError
		} else if task.Status == Ongoing {
			statusCode = http.StatusAccepted
		}
		c.JSON(statusCode, gin.H{
			"task_id":     task.Id,
			"status":      task.Status,
			"job_name":    task.JobName,
			"job_version": task.JobVersion,
			"job_path":    task.JobPath,
			"http_method": task.RequestMethod,
			"started_at":  task.startedAt,
			"ended_at":    task.endedAt,
			"duration":    durationStr,
			"error":       task.ErrorMessage,
			"attempts":    task.Attempts,
		})
	} else if task.Status == Completed {
		for k, v := range task.ResponseHeaders {
			c.Writer.Header().Set(k, v)
		}
		contentType, ok := task.ResponseHeaders["Content-Type"]
		if ok {
			c.Data(*task.ResponseStatusCode, contentType, []byte(task.ResponseBody))
		} else {
			c.Data(*task.ResponseStatusCode, "", []byte(task.ResponseBody))
		}
	}

	if task.Status == Completed || task.Status == Failed {
		go func() {
			// Delete task after short time in case of timeout occured while sending the result to the client
			time.Sleep(30 * time.Second)
			err := taskStore.DeleteTask(task.Id)
			if err != nil {
				logger.Error("Failed to delete async task", log.Ctx{
					"error": err.Error(),
				})
				return
			}
			logger.Info("Retrieved task has been deleted", log.Ctx{
				"status": task.Status,
			})
		}()
	}
}

func respondError(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	statusCode int,
	errorName string,
	err error,
	errorContext map[string]any,
) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logCtxMap := log.Ctx{"requestId": requestId}
	ginCtxMap := gin.H{"requestId": requestId}
	if err == nil {
		ginCtxMap["error"] = errorName
	} else {
		logCtxMap["error"] = err.Error()
		ginCtxMap["error"] = WrapError(errorName, err).Error()
	}
	for k, v := range errorContext {
		logCtxMap[k] = v
		ginCtxMap[k] = v
	}
	logger.Error(errorName, logCtxMap)
	c.JSON(statusCode, ginCtxMap)
}
