package main

import (
	"bytes"
	"encoding/gob"
	"fmt"
	"net/http"
	"net/url"

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
var slaveConnections map[string]*websocket.Conn = make(map[string]*websocket.Conn)

func initRemoteGateway(router *gin.Engine, cfg *Config) {
	router.GET("/pub/slave/ws", func(c *gin.Context) {
		statusCode, err := openSlaveWebsocket(cfg, c.Writer, c.Request)
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

func openSlaveWebsocket(cfg *Config, writer http.ResponseWriter, request *http.Request) (int, error) {
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
		return http.StatusInternalServerError, errors.Wrap(err, "Websocket upgrade failed")
	}
	masterWsConnection = conn
	log.Debug("Master Pub connected to Slave Websocket server")
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

	slaveConn, found := slaveConnections[gatewayHost]
	if !found || slaveConn == nil {
		connectToSlaveWebsocket(cfg, gatewayHost, gatewayUrlTxt, jobCall)
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

// Setup Websocket connection so that Slave can make calls to Master's Lifecycle
func connectToSlaveWebsocket(
	cfg *Config,
	gatewayHost string,
	gatewayUrlTxt string,
	jobCall *JobCallAuthData,
) {
	wsUrl := url.URL{Scheme: "ws", Host: gatewayHost, Path: "/pub/slave/ws"}
	log.Debug("Connecting to slave's websocket", log.Ctx{
		"url": wsUrl.String(),
	})
	requestHeader := http.Header{}
	if jobCall.RemoteGatewayToken != nil {
		requestHeader[RemoteGatewayTokenHeader] = []string{*jobCall.RemoteGatewayToken}
	}
	conn, _, err := websocket.DefaultDialer.Dial(wsUrl.String(), requestHeader)
	if err != nil {
		log.Error("Failed to connect to Slave's websocket", log.Ctx{
			"error": err,
		})
	} else {
		slaveConnections[gatewayUrlTxt] = conn
		log.Info("Connected to slave's websocket", log.Ctx{
			"url": wsUrl.String(),
		})
		go serveGatewayWebsocketCalls(cfg, conn, gatewayHost)
	}
}

func serveGatewayWebsocketCalls(cfg *Config, conn *websocket.Conn, gatewayHost string) {
	for {
		err, fatalError := handleGatewayWebsocketCall(cfg, conn)
		if fatalError != nil {
			if websocket.IsCloseError(fatalError, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				break
			}
			log.Error("Gateway Websocket error, closing connection", log.Ctx{
				"error": fatalError,
			})
			break
		}
		if err != nil {
			log.Error("Gateway Websocket error", log.Ctx{
				"error": err,
			})
		}
	}
	conn.Close()
	slaveConnections[gatewayHost] = nil
	log.Debug("Slave websocket connection closed", log.Ctx{
		"gatewayHost": gatewayHost,
	})
}

// Decode Slave's websocket request and make call to local Lifecycle on his behalf
func handleGatewayWebsocketCall(cfg *Config, conn *websocket.Conn) (err error, fatalError error) {
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
	log.Debug("Websocket message received")

	reader := bytes.NewReader(message)
	decoder := gob.NewDecoder(reader)
	var request SlaveAuthorizeRequest
	err = decoder.Decode(&request)
	if err != nil {
		return errors.Wrap(err, "failed to decode SlaveAuthorizeRequest"), nil
	}

	jobCallAuthData, err := makeMasterLifecycleAuthCall(cfg, &request)
	response := SlaveAuthorizeResponse{
		JobCallAuthData: jobCallAuthData,
		Err:             err,
	}

	var buff bytes.Buffer
	encoder := gob.NewEncoder(&buff)
	err = encoder.Encode(response)
	if err != nil {
		return errors.Wrap(err, "failed to encode SlaveAuthorizeResponse"), nil
	}

	// Send response through websocket
	err = conn.WriteMessage(websocket.BinaryMessage, buff.Bytes())
	if err != nil {
		return errors.Wrap(err, "Websocket write failed"), nil
	}

	log.Debug("Master auth call has been made")
	return nil, nil
}

// Make call to local Lifecycle by Master Pub, commissioned by Slave Pub
func makeMasterLifecycleAuthCall(
	cfg *Config, request *SlaveAuthorizeRequest,
) (jobCallAuthData *JobCallAuthData, err error) {
	lifecycleClient := NewMasterLifecycleClient(cfg.LifecycleUrl, request.AuthToken,
		cfg.LifecycleToken, cfg.RequestTracingHeader, request.RequestId)
	return lifecycleClient.AuthorizeCaller(request.JobName, request.JobVersion, request.Endpoint)
}

type SlaveAuthorizeRequest struct {
	JobName    string
	JobVersion string
	Endpoint   string
	AuthToken  string
	RequestId  string
}

type SlaveAuthorizeResponse struct {
	JobCallAuthData *JobCallAuthData
	Err             error
}

type slaveLifecycleClient struct {
	wsConn        *websocket.Conn
	authToken     string
	internalToken string
	requestId     string
}

// Lifecycle client that makes calls through Master websocket connection
func NewSlaveLifecycleClient(
	authToken string,
	internalToken string,
	requestId string,
) (LifecycleClient, error) {
	if masterWsConnection == nil {
		return nil, errors.New("Master Pub is not subscribed to Slave's Websocket")
	}
	return &slaveLifecycleClient{
		wsConn:        masterWsConnection,
		authToken:     authToken,
		internalToken: internalToken,
		requestId:     requestId,
	}, nil
}

func (l *slaveLifecycleClient) AuthorizeCaller(jobName, jobVersion, endpoint string) (*JobCallAuthData, error) {
	// Encode request to websocket bytes
	var buff bytes.Buffer
	encoder := gob.NewEncoder(&buff)
	err := encoder.Encode(SlaveAuthorizeRequest{
		JobName:    jobName,
		JobVersion: jobVersion,
		Endpoint:   endpoint,
		AuthToken:  l.authToken,
		RequestId:  l.requestId,
	})
	if err != nil {
		return nil, errors.Wrap(err, "failed to encode SlaveAuthorizeRequest")
	}

	// Send request through websocket
	err = l.wsConn.WriteMessage(websocket.BinaryMessage, buff.Bytes())
	if err != nil {
		return nil, errors.Wrap(err, "Websocket write failed")
	}
	log.Debug("Slave auth call has been sent through Websocket")
	// Read response
	_, message, err := l.wsConn.ReadMessage()
	if err != nil {
		return nil, errors.Wrap(err, "Websocket read failed")
	}
	log.Debug("Websocket message received")

	// Decode response
	reader := bytes.NewReader(message)
	decoder := gob.NewDecoder(reader)
	var response SlaveAuthorizeResponse
	err = decoder.Decode(&response)
	if err != nil {
		return nil, errors.Wrap(err, "failed to decode SlaveAuthorizeResponse")
	}

	return response.JobCallAuthData, response.Err
}

func remoteGatewayEndpoint(c *gin.Context, cfg *Config, jobPath string) {
	requestId := getRequestTracingId(c.Request, cfg.RequestTracingHeader)
	logger := log.New(log.Ctx{
		"requestId": requestId,
	})

	logger.Info("Incoming forwarding request from master Pub", log.Ctx{"method": c.Request.Method, "path": c.Request.URL.Path})
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
	return 200, nil
}
