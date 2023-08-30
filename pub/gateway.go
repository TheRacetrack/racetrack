package main

import (
	"bytes"
	"encoding/gob"
	"net/http"
	"net/url"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
)

func init() {
	gob.Register(map[string]interface{}{})
}

const RemoteGatewayTokenHeader = "X-Racetrack-Gateway-Token"

// const JobInternalNameHeader = "X-Racetrack-Job-Internal-Name"

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
}

var masterConn *websocket.Conn = nil
var slaveConnections map[string]*websocket.Conn = make(map[string]*websocket.Conn)

func setupRemoteGateway(router *gin.Engine, cfg *Config) {
	router.GET("/pub/slave/ws", func(c *gin.Context) {
		openSlaveWebsocketServer(c.Writer, c.Request)
	})
	log.Info("Remote gateway mode initialized")
}

func openSlaveWebsocketServer(writer http.ResponseWriter, request *http.Request) {
	if masterConn != nil {
		masterConn.Close()
	}
	// TODO check token header beforehand
	conn, err := upgrader.Upgrade(writer, request, nil)
	if err != nil {
		log.Error("Websocket upgrade failed", log.Ctx{
			"error": err,
		})
		return
	}
	masterConn = conn
	log.Debug("Master Pub has connected to Websocket server")
}

// Forward call to remote infrastructure through PUB gateway
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

	urlStr := JoinURL(gatewayUrlTxt, "/pub/job/", job.Name, job.Version, jobPath)

	// if jobCall.RemoteGatewayToken != nil {
	// 	c.Request.Header.Set(RemoteGatewayTokenHeader, *jobCall.RemoteGatewayToken)
	// }
	// c.Request.Header.Set(JobInternalNameHeader, job.InternalName)

	targetUrl, err := url.Parse(urlStr)
	if err != nil {
		return http.StatusInternalServerError, errors.Wrap(err, "Parsing remote infrastructure address")
	}

	logger.Info("Forwarding call to remote infrastructure", log.Ctx{
		"infrastructureTarget":    job.InfrastructureTarget,
		"infrastructureTargetUrl": gatewayUrlTxt,
		"targetUrl":               urlStr,
		"jobInternalName":         job.InternalName,
	})

	// Ensure Master is connected to this slave
	slaveConn, found := slaveConnections[gatewayHost]
	if !found || slaveConn == nil {

		// Setup Websocket connection so that Slave can ask Master for more details (in case of chain calls)
		wsUrl := url.URL{Scheme: "ws", Host: gatewayHost, Path: "/pub/slave/ws"}
		log.Debug("Connecting to slave's websocket", log.Ctx{
			"url": wsUrl.String(),
		})
		conn, _, err := websocket.DefaultDialer.Dial(wsUrl.String(), nil) // TODO secure with header
		if err != nil {
			log.Error("Failed to connect to Slave's websocket", log.Ctx{
				"error": err,
			})
		} else {
			log.Info("Connected to slave's websocket", log.Ctx{
				"gatewayHost": gatewayHost,
				"url":         wsUrl.String(),
			})
			go func() {
				defer func() {
					conn.Close()
					slaveConnections[gatewayHost] = nil
					log.Debug("Closing slave websocket connection", log.Ctx{
						"gatewayHost": gatewayHost,
					})
				}()
				for {
					err, fatalError := handleWebsocketLifecycleCall(cfg, conn)
					if fatalError != nil {
						log.Error("Websocket error - closing connection", log.Ctx{
							"error": fatalError,
						})
						return
					}
					if err != nil {
						log.Error("Websocket error", log.Ctx{
							"error": err,
						})
					}
				}

			}()
		}
		slaveConnections[gatewayUrlTxt] = conn

	}

	// Forward to remote PUB
	ServeReverseProxy(*targetUrl, c, job, cfg, logger, requestId, callerName)
	return 200, nil
}

func handleWebsocketLifecycleCall(
	cfg *Config,
	conn *websocket.Conn,
) (err error, fatalError error) {
	_, message, err := conn.ReadMessage()
	if err != nil {
		return nil, errors.Wrap(err, "Websocket read failed")
	}
	log.Debug("Websocket message received")

	// Decode request
	reader := bytes.NewReader(message)
	decoder := gob.NewDecoder(reader)
	var request SlaveAuthorizeRequest
	err = decoder.Decode(&request)
	if err != nil {
		return errors.Wrap(err, "failed to decode SlaveAuthorizeRequest"), nil
	}

	// Process request - response
	jobCallAuthData, err := makeMasterLifecycleAuthCall(cfg, &request)
	response := SlaveAuthorizeResponse{
		JobCallAuthData: jobCallAuthData,
		Err:             err,
	}

	// Encode response to websocket bytes
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

func makeMasterLifecycleAuthCall(
	cfg *Config,
	request *SlaveAuthorizeRequest,
) (jobCallAuthData *JobCallAuthData, err error) {
	lifecycleClient := NewLifecycleClient(cfg.LifecycleUrl, request.AuthToken,
		cfg.LifecycleToken, cfg.RequestTracingHeader, request.RequestId)
	return lifecycleClient.AuthorizeCaller(request.JobName, request.JobVersion, request.Endpoint)
}

// Respond to a call forwarded by master
// func handleSlaveGatewayRequest(
// 	c *gin.Context,
// 	cfg *Config,
// 	logger log.Logger,
// 	requestId string,
// 	jobPath string,
// ) (int, error) {

// 	if !cfg.RemoteGatewayMode {
// 		return http.StatusUnauthorized, errors.New("Forwarding endpoint is only available in remote gateway mode")
// 	}

// 	if c.Request.Method != "POST" && c.Request.Method != "GET" {
// 		c.Writer.Header().Set("Allow", "GET, POST")
// 		return http.StatusMethodNotAllowed, errors.New("Method not allowed")
// 	}

// 	jobName := c.Param("job")
// 	if jobName == "" {
// 		return http.StatusBadRequest, errors.New("Couldn't extract job name")
// 	}
// 	jobVersion := c.Param("version")
// 	if jobVersion == "" {
// 		return http.StatusBadRequest, errors.New("Couldn't extract job version")
// 	}

// 	gatewayToken := c.Request.Header.Get(RemoteGatewayTokenHeader)
// 	if gatewayToken == "" {
// 		return http.StatusUnauthorized, errors.Errorf("PUB gateway expects %s header", RemoteGatewayTokenHeader)
// 	}
// 	if gatewayToken != cfg.RemoteGatewayToken {
// 		return http.StatusUnauthorized, errors.New("PUB gateway token is invalid")
// 	}

// 	jobInternalName := c.Request.Header.Get(JobInternalNameHeader)

// 	job := &JobDetails{
// 		Name:         jobName,
// 		Version:      jobVersion,
// 		InternalName: jobInternalName,
// 	}
// 	callerName := c.Request.Header.Get(cfg.CallerNameHeader)

// 	urlPath := JoinURL("/pub/job/", job.Name, job.Version, jobPath)
// 	targetUrl := TargetURL(cfg, job, urlPath)

// 	logger.Debug("Forwarding request to job", log.Ctx{
// 		"jobName":         jobName,
// 		"jobVersion":      jobVersion,
// 		"jobInternalName": jobInternalName,
// 		"targetUrl":       targetUrl.String(),
// 	})

// 	ServeReverseProxy(targetUrl, c, job, cfg, logger, requestId, callerName)
// 	return 200, nil
// }

func handleSlaveProxyRequest(
	c *gin.Context,
	cfg *Config,
	logger log.Logger,
	requestId string,
	jobPath string,
) (int, error) {
	if masterConn == nil {
		return http.StatusInternalServerError, errors.New("Master PUB has not subscribed")
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

	if c.Request.Header.Get("Accept") == "" {
		return http.StatusBadRequest, errors.New("Missing 'Accept' header. " +
			"You might wanted to include 'Accept: application/json, */*' request header.")
	}

	// Get data from Master Lifecycle
	authToken := getAuthFromHeaderOrCookie(c.Request)
	lifecycleClient := NewSlaveLifecycleClient(masterConn, authToken, cfg.LifecycleToken, requestId)

	var job *JobDetails
	var callerName string
	var err error

	jobCall, err := lifecycleClient.AuthorizeCaller(jobName, jobVersion, jobPath)
	if err == nil {
		job = jobCall.Job
		if jobCall.Caller != nil {
			callerName = *jobCall.Caller
		}
		metricAuthSuccessful.Inc()
	} else {
		metricAuthFailed.Inc()
		if errors.As(err, &AuthenticationFailure{}) {
			if cfg.AuthDebug {
				return http.StatusUnauthorized, errors.Wrap(err, "Unauthenticated")
			} else {
				return http.StatusUnauthorized, errors.New("Unauthenticated")
			}
		} else if errors.As(err, &NotFoundError{}) {
			return http.StatusNotFound, errors.Wrap(err, "Job was not found")
		}
		return http.StatusInternalServerError, errors.Wrap(err, "Getting job details")
	}

	metricJobProxyRequests.WithLabelValues(job.Name, job.Version).Inc()

	targetUrl := TargetURL(cfg, job, c.Request.URL.Path)
	ServeReverseProxy(targetUrl, c, job, cfg, logger, requestId, callerName)
	return 200, nil
}

type slaveLifecycleClient struct {
	*lifecycleClient
	wsConn *websocket.Conn
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

func NewSlaveLifecycleClient(
	wsConn *websocket.Conn,
	authToken string,
	internalToken string,
	requestId string,
) LifecycleClient {
	return &slaveLifecycleClient{
		lifecycleClient: &lifecycleClient{
			authToken:     authToken,
			internalToken: internalToken,
			httpClient: &http.Client{
				Timeout: 10 * time.Second,
			},
			requestId: requestId,
		},
		wsConn: wsConn,
	}
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
	err = masterConn.WriteMessage(websocket.BinaryMessage, buff.Bytes())
	if err != nil {
		return nil, errors.Wrap(err, "Websocket write failed")
	}
	log.Debug("Slave auth call has been sent through Websocket")
	// Read response
	_, message, err := masterConn.ReadMessage()
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
