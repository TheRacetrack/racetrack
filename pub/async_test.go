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
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jarcoal/httpmock"
	"github.com/stretchr/testify/assert"
)

func TestMultiReplicasAsyncStore(t *testing.T) {
	replicaNum := 3

	var wgRequestsStarted sync.WaitGroup
	wgRequestsStarted.Add(replicaNum)

	defaultLifecycleTransport = httpmock.DefaultTransport
	defaultJobProxyTransport = httpmock.DefaultTransport
	defaultAsyncJobTransport = httpmock.DefaultTransport

	defer httpmock.DeactivateAndReset()
	httpmock.RegisterResponder("GET", "http://127.0.0.1:7202/lifecycle/api/v1/auth/can-call-job/adder/latest/api/v1/perform",
		httpmock.NewStringResponder(200,
			`{"job": {"id": "000", "name": "adder", "version": "0.0.1", "status": "running", "create_time": 1, "update_time": 1, "manifest": null, "internal_name": "adder-v-0-0-1"}, "caller": "bob"}`))
	httpmock.RegisterResponder("POST", "http://adder-v-0-0-1/pub/job/adder/0.0.1/api/v1/perform",
		func(req *http.Request) (*http.Response, error) {
			status := 200
			body := `{"result": 42}`

			// wait until all replicas asked for a result
			wgRequestsStarted.Wait()

			resp := http.Response{
				Status:        strconv.Itoa(status),
				StatusCode:    status,
				Body:          httpmock.NewRespBodyFromString(body),
				Header:        http.Header{},
				ContentLength: -1,
			}

			resp.Request = req
			return &resp, nil
		})

	addrs := generateReplicaAddresses(replicaNum)
	stores := make([]*AsyncTaskStore, replicaNum)
	servers := make([]*http.Server, replicaNum)

	cfg, err := LoadConfig()
	cfg.LifecycleUrl = "http://127.0.0.1:7202/lifecycle"
	if err != nil {
		panic(err)
	}

	for i := 0; i < replicaNum; i++ {
		replicaDiscovery := NewStaticReplicaDiscovery(addrs)
		stores[i] = NewAsyncTaskStore(replicaDiscovery)
		servers[i] = setupServer(addrs[i], cfg, stores[i])
	}

	response := postJsonRequest(
		fmt.Sprintf("http://%v/pub/async/new/job/adder/latest/api/v1/perform", addrs[0]),
		`{"numbers": [40, 2]}`,
	)
	assert.Equal(t, response.StatusCode, http.StatusCreated) // 201

	responsePayload := readJsonResponse(response)
	assert.Equal(t, responsePayload["status"], "ongoing")
	assert.NotEqual(t, responsePayload["task_id"], "")
	taskId := responsePayload["task_id"].(string)

	var wgActiveRequests sync.WaitGroup
	for i := 0; i < replicaNum; i++ {
		wgActiveRequests.Add(1)
		go func(i int) {
			wgRequestsStarted.Done()
			defer wgActiveRequests.Done()
			statusCode, responsePayload := getJsonRequest(fmt.Sprintf("http://%v/pub/async/task/%v/poll", addrs[i], taskId))
			assert.Equal(t, statusCode, http.StatusOK)
			assert.EqualValues(t, responsePayload["result"], 42)
		}(i)
	}
	wgActiveRequests.Wait()

	for i := 0; i < replicaNum; i++ {
		servers[i].Close()
	}
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

func setupServer(addr string, cfg *Config, store *AsyncTaskStore) *http.Server {
	gin.SetMode(gin.ReleaseMode) // Hide Debug Routings
	router := gin.New()

	SetupEndpoints(router, cfg, "/pub", store)

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
	return response.StatusCode, readJsonResponse(response)
}

func getHttpClient() *http.Client {
	dialer := &net.Dialer{
		Timeout:   30 * time.Second,
		KeepAlive: 30 * time.Second,
	}
	return &http.Client{
		Transport: &http.Transport{
			Proxy:                 http.ProxyFromEnvironment,
			DialContext:           dialer.DialContext,
			ForceAttemptHTTP2:     true,
			MaxIdleConns:          100,
			IdleConnTimeout:       90 * time.Second,
			TLSHandshakeTimeout:   10 * time.Second,
			ExpectContinueTimeout: 1 * time.Second,
		},
	}
}
