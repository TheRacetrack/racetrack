package main

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
	uuid "github.com/satori/go.uuid"
)

var defaultAsyncJobTransport http.RoundTripper = defaultHttpTransport()
var defaultAsyncReplicaTransport http.RoundTripper = defaultHttpTransport()

// Start a new async job call in background and return task ID
func AsyncJobCallEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore, jobPath string) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{"requestId": requestId})
	if strings.HasPrefix(jobPath, "//") {
		jobPath = jobPath[1:]
	}

	logger.Info("Request: new Async Job Call", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleAsyncJobCallRequest(c, cfg, taskStore, logger, requestId, jobPath)
	if err != nil {
		metricAsyncJobCallsErros.Inc()
		respondError(c, cfg, logger, statusCode, "Async Job Call request error", err, map[string]any{
			"path": c.Request.URL.Path,
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
	requestHeaders := make(map[string]string)
	for k, v := range c.Request.Header {
		requestHeaders[k] = strings.Join(v, ",")
	}
	defer c.Request.Body.Close()
	requestBody, err := io.ReadAll(c.Request.Body)
	if err != nil {
		return http.StatusBadRequest, errors.Wrap(err, "failed to read request body")
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
	})
	if err != nil {
		return http.StatusInternalServerError, errors.Wrap(err, "failed to create async task")
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

	go func() {
		err := makeBackgroundJobCall(targetUrl, c, requestBody, job, cfg, taskStore, task, requestId, callerName)

		task.endedAt = ptr(time.Now())
		task.EndedAtTimestamp = ptr(time.Now().Unix())
		if err == nil {
			task.Status = Completed
			metricAsyncJobCallsDone.WithLabelValues(job.Name, job.Version).Inc()
			duration := task.endedAt.Sub(task.startedAt).String()
			logger.Info("Async Job Call task has ended", log.Ctx{
				"taskId":     task.Id,
				"jobName":    job.Name,
				"jobVersion": job.Version,
				"jobPath":    targetUrl.Path,
				"caller":     callerName,
				"statusCode": *task.ResponseStatusCode,
				"duration":   duration,
			})
		} else {
			task.Status = Failed
			errorStr := err.Error()
			task.ErrorMessage = &errorStr
			logger.Error("Background Job Call request error", log.Ctx{
				"taskId":     task.Id,
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
		err = taskStore.UpdateTask(task)
		if err != nil {
			logger.Error("Failed to update async task", log.Ctx{
				"taskId": task.Id,
				"error":  err.Error(),
			})
		}

		// Notify subscribed listeners without blocking
		select {
		case task.doneChannel <- task.Id:
		default:
		}
		close(task.doneChannel)
	}()

	return http.StatusOK, nil
}

func makeBackgroundJobCall(
	target url.URL,
	c *gin.Context,
	requestBody []byte,
	job *JobDetails,
	cfg *Config,
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
	res, err := taskStore.jobHttpClient.Do(req)
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

	task.ResponseStatusCode = ptr(res.StatusCode)
	defer res.Body.Close()
	bodyBytes, err := io.ReadAll(res.Body)
	if err != nil {
		return errors.Wrap(err, "failed to read response body")
	}
	task.ResponseBody = string(bodyBytes)
	task.ResponseHeaders = make(map[string]string)
	for k, v := range res.Header {
		task.ResponseHeaders[k] = strings.Join(v, ",")
	}

	statusCode := strconv.Itoa(res.StatusCode)
	metricJobProxyResponseCodes.WithLabelValues(job.Name, job.Version, statusCode).Inc()
	jobCallTime := time.Since(jobCallStartTime).Seconds()
	metricJobCallResponseTimeHistogram.WithLabelValues(job.Name, job.Version).Observe(jobCallTime)
	metricJobCallResponseTime.WithLabelValues(job.Name, job.Version).Add(jobCallTime)
	metricJobProxyRequestsDone.WithLabelValues(job.Name, job.Version).Inc()
	return nil
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
			c.JSON(http.StatusNotFound, gin.H{
				"error":     fmt.Sprintf("Task with id %s not found", taskId),
				"requestId": getRequestTracingId(c.Request, cfg.RequestTracingHeader),
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
		if replicaAddr == "" {
			respondError(c, cfg, logger, http.StatusNotFound,
				"Task with cannot be located on any replica", nil, map[string]any{
					"taskId": taskId,
				})
			return
		}

		exists, err := checkTaskExistsInReplica(taskStore, replicaAddr, taskId)
		if err != nil {
			respondError(c, cfg, logger, http.StatusInternalServerError,
				"Failed to check async task in other Pub replica", err, map[string]any{
					"replicaAddr": replicaAddr,
					"taskId":      taskId,
				})
			return
		}

		if !exists {
			respondError(c, cfg, logger, http.StatusNotFound,
				"Task not found in a replica", nil, map[string]any{
					"replicaAddr": replicaAddr,
					"taskId":      taskId,
				})
			return
		}

		forwardTaskPollToReplica(c, cfg, logger, taskStore, replicaAddr, taskId)
	}
}

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
			c.JSON(http.StatusNotFound, gin.H{
				"error":     fmt.Sprintf("Task with id %s not found", taskId),
				"requestId": getRequestTracingId(c.Request, cfg.RequestTracingHeader),
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
		if replicaAddr == "" || replicaAddr == taskStore.replicaDiscovery.MyAddr {
			respondError(c, cfg, logger, http.StatusNotFound,
				"Task cannot be located on any replica", nil, map[string]any{
					"taskId": taskId,
				})
			return
		}

		forwardTaskStatusToReplica(c, cfg, logger, taskStore, replicaAddr, taskId)
	}
}

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

// Wait using HTTP Long Polling until task is completed or timeout is reached
// Internal endpoint for communication between Pub replicas
// Ask single replica for task status without forwarding to other replicas
func LocalTaskPollEndpoint(c *gin.Context, cfg *Config, taskStore *AsyncTaskStore, accessLog bool) {
	taskId := c.Param("taskId")
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{"requestId": requestId})
	if accessLog {
		logger.Info("Request: Poll async task of this replica", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	}

	task, ok := taskStore.GetLocalTask(taskId)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{
			"error":     fmt.Sprintf("Task with id %s not found", taskId),
			"requestId": getRequestTracingId(c.Request, cfg.RequestTracingHeader),
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
	case <-time.After(taskStore.longPollTimeout):
		break
	}

	task, ok = taskStore.GetLocalTask(taskId)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{
			"error": fmt.Sprintf("Task with id %s not found", taskId),
		})
		return
	}
	if task.Status == Ongoing {
		c.String(http.StatusRequestTimeout, "Time out")
		return
	} else {
		respondTaskResult(c, logger, task, taskStore)
	}
}

func checkTaskExistsInReplica(
	taskStore *AsyncTaskStore,
	replicaAddr string,
	taskId string,
) (bool, error) {
	url := fmt.Sprintf("http://%s/pub/async/task/%s/status/local", replicaAddr, taskId)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return false, errors.Wrap(err, "failed to create request to Pub replica")
	}
	res, err := taskStore.replicaHttpClient.Do(req)
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

func forwardTaskStatusToReplica(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	taskStore *AsyncTaskStore,
	replicaAddr string,
	taskId string,
) {
	logger.Info("Forwarding async task status to other replica", log.Ctx{
		"taskId":      taskId,
		"replicaAddr": replicaAddr,
	})
	url := fmt.Sprintf("http://%s/pub/async/task/%s/status/local", replicaAddr, taskId)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		respondError(c, cfg, logger, http.StatusServiceUnavailable,
			"Failed to make request to Pub replica", err, map[string]any{
				"taskId": taskId,
				"url":    url,
			})
		return
	}
	res, err := taskStore.replicaHttpClient.Do(req)
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
	logCtxMap := log.Ctx{
		"error":     err.Error(),
		"requestId": requestId,
	}
	ginCtxMap := gin.H{
		"error":     errors.Wrap(err, errorName).Error(),
		"requestId": requestId,
	}
	if err == nil {
		ginCtxMap["error"] = errorName
	} else {
		logCtxMap["error"] = err.Error()
		ginCtxMap["error"] = errors.Wrap(err, errorName).Error()
	}
	for k, v := range errorContext {
		logCtxMap[k] = v
		ginCtxMap[k] = v
	}
	logger.Error(errorName, logCtxMap)
	c.JSON(statusCode, ginCtxMap)
}
