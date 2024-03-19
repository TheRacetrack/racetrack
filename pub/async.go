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
	"time"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	uuid "github.com/satori/go.uuid"
)

// Start a new async job call in background and return task ID
func TaskStartEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore, jobPath string) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{"requestId": requestId})
	if strings.HasPrefix(jobPath, "//") {
		jobPath = jobPath[1:]
	}

	logger.Info("Request: new Async Job Call", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleTaskStartRequest(c, cfg, taskStore, logger, requestId, jobPath)
	if err != nil {
		metricAsyncJobCallsErros.Inc()
		respondError(c, cfg, logger, statusCode, "Async Job Call request error", err, map[string]any{
			"path": c.Request.URL.Path,
		})
	}
}

func handleTaskStartRequest(
	c *gin.Context,
	cfg *Config,
	taskStore *AsyncTaskStore,
	logger log.Logger,
	requestId string,
	jobPath string,
) (int, error) {
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

	job, _, callerName, statusCode, err := getAuthorizedJobDetails(c, cfg, requestId, jobName, jobVersion, jobPath)
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
		Attempts:           0,
		PubInstanceAddr:    taskStore.replicaDiscovery.MyAddr,
		doneChannel:        make(chan string),
		quitChannel:        make(chan bool, 1),
	})
	if err != nil {
		return http.StatusInternalServerError, WrapError("failed to create async task", err)
	}
	logger.Info("Async Job Call task created", log.Ctx{
		"taskId":     task.Id,
		"jobName":    job.Name,
		"jobVersion": job.Version,
		"jobPath":    jobPath,
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

	task.endedAt = ptr(time.Now())
	task.EndedAtTimestamp = ptr(time.Now().Unix())
	task.RetriableError = retriable
	if err == nil {
		task.Status = Completed
		task.ErrorMessage = nil
		metricAsyncJobCallsDone.WithLabelValues(job.Name, job.Version).Inc()
		duration := task.endedAt.Sub(task.startedAt).String()
		logger.Info("Async Job Call task has ended", log.Ctx{
			"taskId":     task.Id,
			"jobName":    job.Name,
			"jobVersion": job.Version,
			"jobPath":    targetUrl.Path,
			"statusCode": *task.ResponseStatusCode,
			"duration":   duration,
		})
	} else {
		task.Status = Failed
		task.ErrorMessage = ptr(err.Error())
		logger.Error("Background Job Call request error", log.Ctx{
			"taskId":     task.Id,
			"jobName":    job.Name,
			"jobVersion": job.Version,
			"host":       targetUrl.Host,
			"path":       targetUrl.Path,
			"error":      err.Error(),
		})
		metricAsyncJobCallsErros.Inc()
	}
	err = taskStore.UpdateTask(task)
	if err != nil {
		logger.Error("Failed to update async task", log.Ctx{
			"taskId": task.Id,
			"error":  err.Error(),
		})
	}

	if task.Status == Failed && task.RetriableError {
		taskStore.DeleteLocalTask(task.Id) // delete locally, so it can be resumed by other replicas
		logger.Info("Async task ended with a retriable error", log.Ctx{
			"taskId": task.Id,
			"error":  *task.ErrorMessage,
		})
		return
	}

	// Notify subscribed listeners without blocking
	select {
	case task.doneChannel <- task.Id:
	default:
	}
	close(task.doneChannel)
}

// Make an HTTP call to the target Job and keep the result of the task
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
			return WrapError("connection broken to a target job", err), true
		}
		return WrapError("making request to a job", err), false
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
	logger := log.New(log.Ctx{"requestId": requestId})
	logger.Info("Request: local async task status", log.Ctx{
		"method": c.Request.Method,
		"path":   c.Request.URL.Path,
	})

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
	logger := log.New(log.Ctx{"requestId": requestId})
	logger.Info("Request: async task status", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})

	task, ok := taskStore.GetLocalTask(taskId)
	if ok {
		c.JSON(http.StatusOK, gin.H{
			"task_id": task.Id,
			"status":  task.Status,
		})
	} else {
		storedTask, err := taskStore.GetStoredTask(taskId)

		if errors.Is(err, ErrAsyncTaskNotFound) {
			respondError(c, cfg, logger, http.StatusNotFound,
				"Task not found in Lifecycle", err, map[string]any{
					"taskId": taskId,
				})
			return
		}
		if err != nil {
			respondError(c, cfg, logger, http.StatusInternalServerError,
				"Failed to check async task in task storage", err, map[string]any{
					"taskId": taskId,
				})
			return
		}
		replicaAddr := storedTask.PubInstanceAddr
		if replicaAddr != "" && replicaAddr == taskStore.replicaDiscovery.MyAddr {
			respondError(c, cfg, logger, http.StatusNotFound,
				"Task cannot be located on any replica", nil, map[string]any{
					"taskId":      taskId,
					"replicaAddr": replicaAddr,
				})
			return
		}
		if replicaAddr == "" {
			err = retryJobCall(cfg, taskStore, storedTask, taskId, requestId)
			if err != nil {
				respondError(c, cfg, logger, http.StatusServiceUnavailable,
					"Failed to retry async task call", err, map[string]any{
						"taskId": taskId,
					})
				return
			}
			c.JSON(http.StatusOK, gin.H{
				"task_id": taskId,
				"status":  storedTask.Status,
			})
			return
		}

		exists, status, err := checkTaskStatusInReplica(taskStore, replicaAddr, taskId)
		if err == nil && exists {
			c.JSON(http.StatusOK, gin.H{
				"task_id": taskId,
				"status":  status,
			})
			return
		}
		log.Error("Task can't be found in a supposed Pub replica", log.Ctx{
			"error":       err,
			"taskId":      taskId,
			"replicaAddr": replicaAddr,
		})
		err = retryJobCall(cfg, taskStore, storedTask, taskId, requestId)
		if err != nil {
			respondError(c, cfg, logger, http.StatusServiceUnavailable,
				"Failed to retry async task call", err, map[string]any{
					"taskId": taskId,
				})
			return
		}
		c.JSON(http.StatusOK, gin.H{
			"task_id": taskId,
			"status":  storedTask.Status,
		})
	}
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
		return false, "", WrapError("failed to make request to Pub replica", err)
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
	logger := log.New(log.Ctx{"requestId": requestId})
	logger.Info("Request: Poll async task", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})

	_, ok := taskStore.GetLocalTask(taskId)
	if ok {
		LocalTaskPollEndpoint(c, cfg, taskStore, false)
	} else {
		storedTask, err := taskStore.GetStoredTask(taskId)

		if errors.Is(err, ErrAsyncTaskNotFound) {
			respondError(c, cfg, logger, http.StatusNotFound,
				"Task not found in Lifecycle", err, map[string]any{
					"taskId": taskId,
				})
			return
		}
		if err != nil {
			respondError(c, cfg, logger, http.StatusInternalServerError,
				"Failed to check async task in task storage", err, map[string]any{
					"taskId": taskId,
				})
			return
		}
		replicaAddr := storedTask.PubInstanceAddr
		if replicaAddr != "" && replicaAddr == taskStore.replicaDiscovery.MyAddr {
			respondError(c, cfg, logger, http.StatusNotFound,
				"Task cannot be located on any replica", nil, map[string]any{
					"taskId":      taskId,
					"replicaAddr": replicaAddr,
				})
			return
		}
		if replicaAddr == "" {
			replicaAddr = fmt.Sprintf("127.0.0.1:%s", cfg.ListenPort)
		}

		exists, _, err := checkTaskStatusInReplica(taskStore, replicaAddr, taskId)
		if err != nil {
			respondError(c, cfg, logger, http.StatusInternalServerError,
				"Failed to check async task in a supposed Pub replica", err, map[string]any{
					"replicaAddr": replicaAddr,
					"taskId":      taskId,
				})
			return
		}
		if !exists {
			respondError(c, cfg, logger, http.StatusNotFound,
				"Task not found in a supposed replica", nil, map[string]any{
					"replicaAddr": replicaAddr,
					"taskId":      taskId,
				})
			return
		}

		forwardTaskPollToReplica(c, cfg, logger, taskStore, replicaAddr, taskId)
	}
}

// Wait using HTTP Long Polling until task is completed or timeout is reached.
// It's an internal endpoint used for communication between Pub replicas.
// It checks the result locally and does not search in other replicas.
func LocalTaskPollEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore, accessLog bool) {
	taskId := c.Param("taskId")
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{"requestId": requestId})
	if accessLog {
		logger.Info("Request: Polling local async task", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	}

	task, ok := taskStore.GetLocalTask(taskId)
	if !ok {
		respondError(c, cfg, logger, http.StatusNotFound,
			"Task not found locally", nil, map[string]any{
				"taskId": taskId,
			})
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
		log.Info("Task not found locally after time-out", log.Ctx{
			"taskId": taskId,
		})
		c.String(http.StatusRequestTimeout, "Time out")
		return
	}
	if task.Status == Ongoing {
		c.String(http.StatusRequestTimeout, "Time out")
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
		"taskId":      taskId,
		"replicaAddr": replicaAddr,
	})
	url := fmt.Sprintf("http://%s/pub/async/task/%s/poll/local", replicaAddr, taskId)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		respondError(c, cfg, logger, http.StatusServiceUnavailable,
			"Failed to make request to Pub replica", err, map[string]any{
				"taskId": taskId,
				"url":    url,
			})
		return
	}
	res, err := taskStore.replicaPollHttpClient.Do(req)
	if err != nil {
		respondError(c, cfg, logger, http.StatusServiceUnavailable,
			"Failed to make request to Pub replica", err, map[string]any{
				"taskId": taskId,
				"url":    url,
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
			"Failed to read response body", err, map[string]any{
				"taskId": taskId,
			})
		return
	}
	c.Data(res.StatusCode, res.Header.Get("Content-Type"), bodyBytes)
}

func retryJobCall(
	cfg *Config,
	taskStore *AsyncTaskStore,
	task *AsyncTask,
	taskId string,
	requestId string,
) error {
	if task.Attempts >= 1 {
		return errors.New("maximum number of attempts has been exceeded")
	}
	if task.Status == Failed && !task.RetriableError {
		return errors.New("task has failed with non-retriable error")
	}

	task.Attempts++
	task.PubInstanceAddr = taskStore.replicaDiscovery.MyAddr
	task.Status = Ongoing
	task.doneChannel = make(chan string)
	log.Info("Retrying attempt of async job call", log.Ctx{
		"taskId":      taskId,
		"jobName":     task.JobName,
		"jobVersion":  task.JobVersion,
		"jobPath":     task.JobPath,
		"attempts":    task.Attempts,
		"replicaAddr": task.PubInstanceAddr,
	})

	requestBody := []byte(task.RequestBody)
	urlPath := JoinURL("/pub/job/", task.JobName, task.JobVersion, task.JobPath)
	job, err := getJobDetails(cfg, task.JobName, task.JobVersion)
	if err != nil {
		return WrapError("failed to get job details", err)
	}
	targetUrl := TargetURL(cfg, job, urlPath)

	err = taskStore.UpdateTask(task)
	if err != nil {
		return WrapError("failed to update async task", err)
	}

	go func() {
		err, retriable := makeJobCall(targetUrl, requestBody, cfg, taskStore, task, requestId)

		task.endedAt = ptr(time.Now())
		task.EndedAtTimestamp = ptr(time.Now().Unix())
		task.RetriableError = retriable
		if err == nil {
			task.Status = Completed
			task.ErrorMessage = nil
			metricAsyncJobCallsDone.WithLabelValues(task.JobName, task.JobVersion).Inc()
			duration := task.endedAt.Sub(task.startedAt).String()
			log.Info("Async Job Call task has ended", log.Ctx{
				"taskId":     task.Id,
				"jobName":    task.JobName,
				"jobVersion": task.JobVersion,
				"jobPath":    task.JobPath,
				"statusCode": *task.ResponseStatusCode,
				"duration":   duration,
			})
		} else {
			task.Status = Failed
			task.ErrorMessage = ptr(err.Error())
			log.Error("Background Job Call request error", log.Ctx{
				"taskId":     task.Id,
				"jobName":    task.JobName,
				"jobVersion": task.JobVersion,
				"host":       targetUrl.Host,
				"path":       targetUrl.Path,
				"error":      err.Error(),
			})
			metricAsyncJobCallsErros.Inc()
		}
		err = taskStore.UpdateTask(task)
		if err != nil {
			log.Error("Failed to update async task", log.Ctx{
				"taskId": task.Id,
				"error":  err.Error(),
			})
		}

		select { // Notify subscribed listeners without blocking
		case task.doneChannel <- task.Id:
		default:
		}
		close(task.doneChannel)
	}()
	return nil
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
					"taskId": task.Id,
					"error":  err.Error(),
				})
				return
			}
			logger.Info("Retrieved task has been deleted", log.Ctx{
				"taskId": task.Id,
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
