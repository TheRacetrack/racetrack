package main

import (
	"bytes"
	"encoding/gob"
	"fmt"
	"net/http"
	"net/url"
	"os/exec"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

func init() {
	gob.Register(map[string]interface{}{})
}

const RemoteGatewayTokenHeader = "X-Racetrack-Gateway-Token"
const JobInternalNameHeader = "X-Racetrack-Job-Internal-Name"

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
}

var masterWsConnection *websocket.Conn = nil
var remoteConnections map[string]*websocket.Conn = make(map[string]*websocket.Conn)

func initRemoteGateway(router *gin.Engine, cfg *Config) {
	router.GET("/pub/remote/ws", func(c *gin.Context) {
		statusCode, err := openRemoteWebsocket(cfg, c.Writer, c.Request)
		if err != nil {
			log.Error("Failed to open websocket server", log.Ctx{
				"status": statusCode,
				"error":  err.Error(),
			})
			c.JSON(statusCode, gin.H{
				"error":  fmt.Sprintf("Failed to open websocket server: %s", err.Error()),
				"status": http.StatusText(statusCode),
			})
		}
	})
	log.Info("Initialized Remote gateway mode")
}

func openRemoteWebsocket(cfg *Config, writer http.ResponseWriter, request *http.Request) (int, error) {
	if masterWsConnection != nil {
		masterWsConnection.Close()
	}
	gatewayToken := request.Header.Get(RemoteGatewayTokenHeader)
	if gatewayToken == "" {
		return http.StatusUnauthorized, errors.Errorf("Pub gateway expects %s header", RemoteGatewayTokenHeader)
	}
	if gatewayToken != cfg.RemoteGatewayToken {
		return http.StatusUnauthorized, errors.New("Pub gateway token is invalid")
	}
	conn, err := upgrader.Upgrade(writer, request, nil)
	if err != nil {
		return http.StatusInternalServerError, errors.Wrap(err, "websocket upgrade failed")
	}
	masterWsConnection = conn
	log.Debug("Main Pub connected to remote websocket server")
	return http.StatusOK, nil
}

// Forward call to remote infrastructure through Pub gateway
func handleMasterProxyRequest(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	requestId string,
	jobPath string,
	jobCall *JobCallAuthData,
	job *JobDetails,
	callerName string,
) (int, error) {
	gatewayUrlTxt := *jobCall.RemoteGatewayUrl
	gatewayUrl, err := url.Parse(gatewayUrlTxt)
	if err != nil {
		return http.StatusInternalServerError, errors.Wrap(err, "Parsing remote gateway URL")
	}
	var gatewayHost string = gatewayUrl.Host

	if jobCall.RemoteGatewayToken != nil {
		c.Request.Header.Set(RemoteGatewayTokenHeader, *jobCall.RemoteGatewayToken)
	}

	remoteConn, found := remoteConnections[gatewayHost]
	if !found || remoteConn == nil {
		connectToRemoteWebsocket(cfg, gatewayHost, jobCall)
	}

	urlStr := JoinURL(gatewayUrlTxt, "/pub/job/", job.Name, job.Version, jobPath)
	targetUrl, err := url.Parse(urlStr)
	if err != nil {
		return http.StatusInternalServerError, errors.Wrap(err, "Parsing remote infrastructure address")
	}
	logger.Info("Forwarding call to remote infrastructure", log.Ctx{
		"infrastructureTarget": job.InfrastructureTarget,
		"targetUrl":            urlStr,
		"jobInternalName":      job.InternalName,
	})

	ServeReverseProxy(*targetUrl, c, job, cfg, logger, requestId, callerName)
	return http.StatusOK, nil
}

// Setup Websocket connection so that remote can make calls to main Lifecycle
func connectToRemoteWebsocket(
	cfg *Config,
	gatewayHost string,
	jobCall *JobCallAuthData,
) {
	wsUrl := url.URL{Scheme: "ws", Host: gatewayHost, Path: "/pub/remote/ws"}
	log.Debug("Connecting to remote websocket", log.Ctx{
		"url": wsUrl.String(),
	})
	requestHeader := http.Header{}
	if jobCall.RemoteGatewayToken != nil {
		requestHeader[RemoteGatewayTokenHeader] = []string{*jobCall.RemoteGatewayToken}
	}
	conn, _, err := websocket.DefaultDialer.Dial(wsUrl.String(), requestHeader)
	if err != nil {
		log.Error("Failed to connect to remote websocket", log.Ctx{
			"error": err,
		})
	} else {
		remoteConnections[gatewayHost] = conn
		log.Info("Connected to remote websocket", log.Ctx{
			"url": wsUrl.String(),
		})
		go serveGatewayWebsocketCalls(cfg, conn, gatewayHost)
	}
}

func serveGatewayWebsocketCalls(cfg *Config, conn *websocket.Conn, gatewayHost string) {
	for {
		err, fatalError := handleGatewayWebsocketCall(cfg, conn, gatewayHost)
		if fatalError != nil {
			if websocket.IsCloseError(fatalError, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				break
			}
			log.Error("Gateway websocket error, closing connection", log.Ctx{
				"error": fatalError,
			})
			break
		}
		if err != nil {
			log.Error("Gateway websocket error", log.Ctx{
				"error": err,
			})
		}
	}
	conn.Close()
	remoteConnections[gatewayHost] = nil
	log.Debug("Connection closed to remote websocket", log.Ctx{
		"gatewayHost": gatewayHost,
	})
}

// Decode remote websocket request and make call to local Lifecycle on his behalf
func handleGatewayWebsocketCall(cfg *Config, conn *websocket.Conn, gatewayHost string) (err error, fatalError error) {
	_, message, err := conn.ReadMessage()
	if err != nil {
		if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
			return nil, errors.Wrap(err, "Websocket closed unexpectedly")
		}
		if websocket.IsCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
			return nil, err
		}
		return nil, errors.Wrap(err, "Websocket read failed")
	}

	reader := bytes.NewReader(message)
	decoder := gob.NewDecoder(reader)
	var request RemoteAuthorizeRequest
	err = decoder.Decode(&request)
	if err != nil {
		return errors.Wrap(err, "failed to decode RemoteAuthorizeRequest"), nil
	}

	jobCallAuthData, err := makeMasterLifecycleAuthCall(cfg, &request)
	response := RemoteAuthorizeResponse{
		JobCallAuthData: jobCallAuthData,
	}
	if err != nil {
		errorCode := http.StatusOK
		if errors.As(err, &AuthenticationFailure{}) {
			errorCode = http.StatusUnauthorized
		} else if errors.As(err, &NotFoundError{}) {
			errorCode = http.StatusNotFound
		}
		response.ErrorDetails = err.Error()
		response.ErrorCode = errorCode
	}

	var buff bytes.Buffer
	encoder := gob.NewEncoder(&buff)
	err = encoder.Encode(response)
	if err != nil {
		return errors.Wrap(err, "failed to encode RemoteAuthorizeResponse"), nil
	}

	// Send response through websocket
	err = conn.WriteMessage(websocket.BinaryMessage, buff.Bytes())
	if err != nil {
		return errors.Wrap(err, "Websocket write failed"), nil
	}

	log.Debug("Lifecycle call made on behalf of remote Pub", log.Ctx{
		"remoteGateway": gatewayHost,
	})
	return nil, nil
}

// Make call to local Lifecycle by main Pub, commissioned by remote Pub
func makeMasterLifecycleAuthCall(
	cfg *Config, request *RemoteAuthorizeRequest,
) (jobCallAuthData *JobCallAuthData, err error) {
	lifecycleClient := NewMasterLifecycleClient(cfg.LifecycleUrl, request.AuthToken,
		cfg.LifecycleToken, cfg.RequestTracingHeader, request.RequestId)
	return lifecycleClient.AuthorizeCaller(request.JobName, request.JobVersion, request.Endpoint)
}

type RemoteAuthorizeRequest struct {
	JobName    string
	JobVersion string
	Endpoint   string
	AuthToken  string
	RequestId  string
}

type RemoteAuthorizeResponse struct {
	JobCallAuthData *JobCallAuthData
	ErrorDetails    string
	ErrorCode       int
}

type remoteLifecycleClient struct {
	wsConn    *websocket.Conn
	authToken string
	requestId string
}

func NewRemoteLifecycleClient(
	authToken string,
	requestId string,
) (LifecycleClient, error) {
	if masterWsConnection == nil {
		return nil, errors.New("Main Pub is not subscribed to remote websocket")
	}
	return &remoteLifecycleClient{
		wsConn:    masterWsConnection,
		authToken: authToken,
		requestId: requestId,
	}, nil
}

// Make call to Lifecycle through master websocket connection
func (l *remoteLifecycleClient) AuthorizeCaller(jobName, jobVersion, endpoint string) (*JobCallAuthData, error) {
	var buff bytes.Buffer
	encoder := gob.NewEncoder(&buff)
	err := encoder.Encode(RemoteAuthorizeRequest{
		JobName:    jobName,
		JobVersion: jobVersion,
		Endpoint:   endpoint,
		AuthToken:  l.authToken,
		RequestId:  l.requestId,
	})
	if err != nil {
		return nil, errors.Wrap(err, "failed to encode RemoteuthorizeRequest to bytes")
	}

	log.Debug("Making Lifecycle call through main websocket connection")
	err = l.wsConn.WriteMessage(websocket.BinaryMessage, buff.Bytes())
	if err != nil {
		return nil, errors.Wrap(err, "failed to send request through main websocket")
	}

	_, message, err := l.wsConn.ReadMessage()
	if err != nil {
		return nil, errors.Wrap(err, "failed to read response from main websocket")
	}

	reader := bytes.NewReader(message)
	decoder := gob.NewDecoder(reader)
	var response RemoteAuthorizeResponse
	err = decoder.Decode(&response)
	if err != nil {
		return nil, errors.Wrap(err, "failed to decode RemoteAuthorizeResponse from bytes")
	}

	if response.ErrorDetails != "" {
		var err error
		if response.ErrorCode == http.StatusUnauthorized {
			err = AuthenticationFailure{errors.New(response.ErrorDetails)}
		} else if response.ErrorCode == http.StatusNotFound {
			err = NotFoundError{errors.New(response.ErrorDetails)}
		} else {
			err = errors.New(response.ErrorDetails)
		}
		return response.JobCallAuthData, err
	}

	return response.JobCallAuthData, nil
}

func remoteGatewayEndpoint(c *gin.Context, cfg *Config, jobPath string) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})

	logger.Info("Incoming forwarding request from main Pub", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleRemoteGatewayRequest(c, cfg, logger, requestId, jobPath)
	if err != nil {
		errorStr := err.Error()
		logger.Error("Proxy request error", log.Ctx{
			"status": statusCode,
			"error":  errorStr,
			"path":   c.Request.URL.Path,
		})
		c.JSON(statusCode, gin.H{
			"error":     fmt.Sprintf("Proxy request error: %s", errorStr),
			"status":    http.StatusText(statusCode),
			"requestId": requestId,
		})
	}
}

func handleRemoteGatewayRequest(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	requestId string,
	jobPath string,
) (int, error) {
	if !cfg.RemoteGatewayMode {
		return http.StatusUnauthorized, errors.New("Forwarding endpoint is only available in remote gateway mode")
	}

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

	gatewayToken := c.Request.Header.Get(RemoteGatewayTokenHeader)
	if gatewayToken == "" {
		return http.StatusUnauthorized, errors.Errorf("Pub gateway expects token in %s header", RemoteGatewayTokenHeader)
	}
	if gatewayToken != cfg.RemoteGatewayToken {
		return http.StatusUnauthorized, errors.New("Pub gateway token is invalid")
	}

	jobInternalName := c.Request.Header.Get(JobInternalNameHeader)
	if jobInternalName == "" {
		return http.StatusBadRequest, errors.Errorf("Pub gateway expects job name in %s header", JobInternalNameHeader)
	}

	job := &JobDetails{
		Name:         jobName,
		Version:      jobVersion,
		InternalName: jobInternalName,
	}
	callerName := c.Request.Header.Get(cfg.CallerNameHeader)

	urlPath := JoinURL("/pub/job/", job.Name, job.Version, jobPath)
	targetUrl := TargetURL(cfg, job, urlPath)

	logger.Debug("Forwarding request to job", log.Ctx{
		"jobName":         jobName,
		"jobVersion":      jobVersion,
		"jobInternalName": jobInternalName,
		"targetUrl":       targetUrl.String(),
	})

	ServeReverseProxy(targetUrl, c, job, cfg, logger, requestId, callerName)
	return http.StatusOK, nil
}

// A command called remotely by Racetrack host to manage infrastructure target
func remoteCommandEndpoint(c *gin.Context, cfg *Config) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})

	logger.Info("Incoming remote command", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
	statusCode, err := handleRemoteCommandRequest(c, cfg, logger, requestId)
	if err != nil {
		errorStr := err.Error()
		logger.Error("Remote command error", log.Ctx{
			"status": statusCode,
			"error":  errorStr,
			"path":   c.Request.URL.Path,
		})
		c.JSON(statusCode, gin.H{
			"error":     fmt.Sprintf("Remote command: %s", errorStr),
			"status":    http.StatusText(statusCode),
			"requestId": requestId,
		})
	}
}

type remoteCommandRequest struct {
	Command string `json:"command"`
}

func handleRemoteCommandRequest(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	requestId string,
) (int, error) {
	gatewayToken := c.Request.Header.Get(RemoteGatewayTokenHeader)
	if gatewayToken == "" {
		return http.StatusUnauthorized, errors.Errorf("remote Pub expects token in %s header", RemoteGatewayTokenHeader)
	}
	if gatewayToken != cfg.RemoteGatewayToken {
		return http.StatusUnauthorized, errors.New("remote Pub token is invalid")
	}

	var request remoteCommandRequest
	err := c.BindJSON(&request)
	if err != nil {
		return http.StatusBadRequest, errors.Wrap(err, "failed to parse request data as JSON")
	}
	if request.Command == "" {
		return http.StatusBadRequest, errors.New("command field is empty")
	}

	logger.Debug("Executing remote command", log.Ctx{
		"command": request.Command,
	})
	cmd := exec.Command("sh", "-c", request.Command)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return http.StatusInternalServerError, errors.Wrapf(err, "command failed: %s: %s", request.Command, output)
	}

	c.JSON(http.StatusOK, gin.H{
		"output":    string(output),
		"exit_code": cmd.ProcessState.ExitCode(),
		"requestId": requestId,
	})
	return http.StatusOK, nil
}
