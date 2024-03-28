package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"strconv"
	"sync"
	"sync/atomic"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/jarcoal/httpmock"
	"github.com/stretchr/testify/assert"
)

func TestMultiReplicasAsyncStore(t *testing.T) {
	replicaNum := 3
	var wgResultRequested sync.WaitGroup
	wgResultRequested.Add(replicaNum)

	addrs := generateReplicaAddresses(replicaNum)
	servers := make([]*http.Server, replicaNum)
	cfg, _ := LoadConfig()
	cfg.LifecycleUrl = "http://127.0.0.1:7202/lifecycle"
	activateMockResponsesWithDelay(&wgResultRequested)
	defer httpmock.DeactivateAndReset()
	taskStorage := NewMemoryTaskStorage()

	for i := 0; i < replicaNum; i++ {
		replicaDiscovery := NewStaticReplicaDiscovery(addrs, addrs[i])
		store := NewAsyncTaskStore(replicaDiscovery, taskStorage)
		servers[i] = setupReplicaServer(addrs[i], cfg, store)
	}

	response := postJsonRequest(
		fmt.Sprintf("http://%v/pub/async/new/job/adder/latest/api/v1/perform", addrs[0]),
		`{"numbers": [40, 2]}`,
	)
	assert.Equal(t, response.StatusCode, http.StatusCreated, "async job call task should be created")
	responsePayload := readJsonResponse(response)
	assert.Equal(t, responsePayload["status"], "ongoing", "new task should have ongoing status")
	taskId := responsePayload["task_id"].(string)

	var wgPollingRequests sync.WaitGroup
	for i := 0; i < replicaNum; i++ {
		wgPollingRequests.Add(1)
		go func(i int) {
			defer wgPollingRequests.Done()
			statusCode, responsePayload := getJsonRequest(fmt.Sprintf("http://%v/pub/async/task/%v/status", addrs[i], taskId))
			assert.Equal(t, statusCode, http.StatusOK, "job result should return status 200")
			assert.EqualValues(t, responsePayload["status"], "ongoing", "task should report ongoing status")
			wgResultRequested.Done()
			statusCode, responsePayload = getJsonRequest(fmt.Sprintf("http://%v/pub/async/task/%v/poll", addrs[i], taskId))
			assert.Equal(t, statusCode, http.StatusOK, "job result should return status 200")
			assert.EqualValues(t, responsePayload["result"], 42, "result data should be included in the job response")
		}(i)
	}
	wgPollingRequests.Wait()

	statusCode, _ := getJsonRequest(fmt.Sprintf("http://%v/pub/async/task/%v/poll", addrs[0], "no-such-task"))
	assert.Equal(t, statusCode, http.StatusNotFound, "should return status 404 for not existing task")

	for i := 0; i < replicaNum; i++ {
		servers[i].Close()
	}
}

func TestRetryCrashedJobCall(t *testing.T) {
	addrs := generateReplicaAddresses(1)
	cfg, _ := LoadConfig()
	cfg.AsyncTaskRetryInterval = 0
	cfg.LifecycleUrl = "http://127.0.0.1:7202/lifecycle"
	jobCallCounter := activateMockJobCrash()
	defer httpmock.DeactivateAndReset()
	taskStorage := NewMemoryTaskStorage()
	replicaDiscovery := NewStaticReplicaDiscovery(addrs, addrs[0])
	store := NewAsyncTaskStore(replicaDiscovery, taskStorage)
	server := setupReplicaServer(addrs[0], cfg, store)
	defer server.Close()

	response := postJsonRequest(
		fmt.Sprintf("http://%v/pub/async/new/job/windows12/latest/api/v1/perform", addrs[0]),
		`{"numbers": [40, 2]}`)
	assert.Equal(t, response.StatusCode, http.StatusCreated, "async job call task should be created")
	taskId := readJsonResponse(response)["task_id"].(string)

	statusCode, responsePayload := getJsonRequest(fmt.Sprintf("http://%v/pub/async/task/%v/poll", addrs[0], taskId))
	assert.Equal(t, statusCode, http.StatusOK, "job result should return status 200")
	assert.EqualValues(t, responsePayload["result"], 42, "result data should be included in the job response")

	task, err := store.GetStoredTask(taskId)
	assert.Nil(t, err, "task should be found in the store")
	assert.EqualValues(t, task.Attempts, 2, "task has been tried twice")
	assert.EqualValues(t, jobCallCounter.Load(), 2, "job has been called twice")
}

func TestResumeMissingTask(t *testing.T) {
	addrs := generateReplicaAddresses(1)
	cfg, _ := LoadConfig()
	cfg.AsyncTaskRetryInterval = 0
	cfg.LifecycleUrl = "http://127.0.0.1:7202/lifecycle"
	var wgResultRequested sync.WaitGroup
	wgResultRequested.Add(1)
	activateMockResponsesWithDelay(&wgResultRequested)
	defer httpmock.DeactivateAndReset()
	taskStorage := NewMemoryTaskStorage()
	replicaDiscovery := NewStaticReplicaDiscovery(addrs, addrs[0])
	store := NewAsyncTaskStore(replicaDiscovery, taskStorage)
	server := setupReplicaServer(addrs[0], cfg, store)

	response := postJsonRequest( // Start a task
		fmt.Sprintf("http://%v/pub/async/new/job/adder/latest/api/v1/perform", addrs[0]),
		`{"numbers": [40, 2]}`)
	assert.Equal(t, response.StatusCode, http.StatusCreated, "async job call task should be created")
	taskId := readJsonResponse(response)["task_id"].(string)

	server.Close() // Restart server to clear local in-memory tasks
	store = NewAsyncTaskStore(replicaDiscovery, taskStorage)
	server = setupReplicaServer(addrs[0], cfg, store)
	defer server.Close()
	assert.EqualValues(t, len(store.localTasks), 0, "local tasks should be empty after server restart")

	go func() {
		for { // wait until task is resumed and then release the job result
			if len(store.localTasks) > 0 {
				break
			}
		}
		wgResultRequested.Done()
	}()

	statusCode, responsePayload := getJsonRequest(fmt.Sprintf("http://%v/pub/async/task/%v/poll", addrs[0], taskId))
	assert.Equal(t, statusCode, http.StatusOK, "job result should return status 200")
	assert.EqualValues(t, responsePayload["result"], 42, "result data should be included in the job response")

	task, err := store.GetStoredTask(taskId)
	assert.Nil(t, err, "task should be found in the store")
	assert.EqualValues(t, task.Attempts, 2, "task has been tried twice")
}

func generateReplicaAddresses(num int) []string {
	return MapSlice(getFreePorts(num), func(port int) string {
		return fmt.Sprintf("127.0.0.1:%v", port)
	})
}

func getFreePorts(num int) []int {
	listeners := make([]*net.TCPListener, num)
	ports := make([]int, num)
	for i := 0; i < num; i++ {
		addr, err := net.ResolveTCPAddr("tcp", "localhost:0")
		if err != nil {
			panic(err)
		}
		listener, err := net.ListenTCP("tcp", addr)
		if err != nil {
			panic(err)
		}
		listeners[i] = listener
		ports[i] = listener.Addr().(*net.TCPAddr).Port
	}
	for _, listener := range listeners {
		listener.Close()
	}
	return ports
}

func activateMockResponsesWithDelay(wgResultRequested *sync.WaitGroup) {
	defaultLifecycleTransport = httpmock.DefaultTransport
	defaultAsyncJobTransport = httpmock.DefaultTransport
	httpmock.RegisterResponder("GET", "http://127.0.0.1:7202/lifecycle/api/v1/auth/can-call-job/adder/latest/api/v1/perform",
		httpmock.NewStringResponder(200, `{"job":
		{"id": "0", "name": "adder", "version": "0.0.1", "status": "running", "create_time": 1,
		"update_time": 1, "manifest": null, "internal_name": "adder-v-0-0-1"}, "caller": "bob"}`))
	httpmock.RegisterResponder("GET", "http://127.0.0.1:7202/lifecycle/api/v1/job/adder/0.0.1",
		httpmock.NewStringResponder(200, `{"id": "0", "name": "adder", "version": "0.0.1",
		"status": "running", "create_time": 1, "update_time": 1, "manifest": null, "internal_name": "adder-v-0-0-1"}`))
	httpmock.RegisterResponder("POST", "http://adder-v-0-0-1/pub/job/adder/0.0.1/api/v1/perform",
		func(req *http.Request) (*http.Response, error) {
			wgResultRequested.Wait() // finish job task only after all replicas subscribed for a result
			return &http.Response{
				Status:        strconv.Itoa(200),
				StatusCode:    200,
				Body:          httpmock.NewRespBodyFromString(`{"result": 42}`),
				Header:        http.Header{},
				ContentLength: -1,
				Request:       req,
			}, nil
		})
}

func setupReplicaServer(addr string, cfg *Config, taskStore *AsyncTaskStore) *http.Server {
	gin.SetMode(gin.ReleaseMode) // Hide Debug Routings
	router := gin.New()
	SetupEndpoints(router, cfg, "/pub", taskStore)

	server := &http.Server{
		Addr:    addr,
		Handler: router,
	}
	ln, err := net.Listen("tcp", server.Addr)
	if err != nil {
		panic(err)
	}
	go func(addr string) {
		if err := server.Serve(ln); err != nil {
			if err == http.ErrServerClosed {
				fmt.Printf("Server %s closed\n", addr)
			} else {
				panic(err)
			}
		}
	}(addr)
	return server
}

func postJsonRequest(url string, content string) *http.Response {
	var jsonData = []byte(content)
	request, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		panic(err)
	}
	request.Header.Set("Content-Type", "application/json; charset=UTF-8")
	client := &http.Client{}
	response, err := client.Do(request)
	if err != nil {
		panic(err)
	}
	return response
}

func readJsonResponse(response *http.Response) map[string]interface{} {
	defer response.Body.Close()
	body, err := io.ReadAll(response.Body)
	if err != nil {
		panic(err)
	}
	responsePayload := make(map[string]interface{})
	json.Unmarshal(body, &responsePayload)
	return responsePayload
}

func getJsonRequest(url string) (int, map[string]interface{}) {
	request, err := http.NewRequest("GET", url, nil)
	if err != nil {
		panic(err)
	}
	client := &http.Client{}
	response, err := client.Do(request)
	if err != nil {
		panic(err)
	}
	if response.StatusCode != 200 {
		defer response.Body.Close()
		bodyBytes, _ := io.ReadAll(response.Body)
		fmt.Printf("Response %d for %s: %s\n", response.StatusCode, url, bodyBytes)
	}
	return response.StatusCode, readJsonResponse(response)
}

func activateMockJobCrash() *atomic.Uint64 {
	defaultLifecycleTransport = httpmock.DefaultTransport
	defaultAsyncJobTransport = httpmock.DefaultTransport
	httpmock.RegisterResponder("GET", "http://127.0.0.1:7202/lifecycle/api/v1/auth/can-call-job/windows12/latest/api/v1/perform",
		httpmock.NewStringResponder(200, `{"job": 
		{"id": "0", "name": "windows12", "version": "0.0.1", "status": "running", "create_time": 1,
		"update_time": 1, "manifest": null, "internal_name": "windows12-v-0-0-1"}, "caller": "bob"}`))
	httpmock.RegisterResponder("GET", "http://127.0.0.1:7202/lifecycle/api/v1/job/windows12/0.0.1",
		httpmock.NewStringResponder(200, `{"id": "0", "name": "windows12", "version": "0.0.1",
		"status": "running", "create_time": 1, "update_time": 1, "manifest": null, "internal_name": "windows12-v-0-0-1"}`))
	var jobCallCounter atomic.Uint64
	httpmock.RegisterResponder("POST", "http://windows12-v-0-0-1/pub/job/windows12/0.0.1/api/v1/perform",
		func(req *http.Request) (*http.Response, error) {
			jobCallCounter.Add(1)
			if jobCallCounter.Load() == 1 {
				return nil, io.EOF
			}
			return &http.Response{
				Status:        strconv.Itoa(200),
				StatusCode:    200,
				Body:          httpmock.NewRespBodyFromString(`{"result": 42}`),
				Header:        http.Header{},
				ContentLength: -1,
				Request:       req,
			}, nil
		})
	return &jobCallCounter
}
