package main

import (
	"encoding/json"
	"io"
	"net/http"
	"time"

	"github.com/pkg/errors"
)

var defaultLifecycleTransport http.RoundTripper = defaultHttpTransport()

type JobCallAuthData struct {
	Job                *JobDetails `json:"job"`
	Caller             *string     `json:"caller"`
	RemoteGatewayUrl   *string     `json:"remote_gateway_url"`
	RemoteGatewayToken *string     `json:"remote_gateway_token"`
}

type JobDetails struct {
	Id                   string      `json:"id"`
	Name                 string      `json:"name"`
	Version              string      `json:"version"`
	Status               string      `json:"status"`
	CreateTime           int         `json:"create_time"`
	UpdateTime           int         `json:"update_time"`
	Manifest             interface{} `json:"manifest"`
	InternalName         string      `json:"internal_name"`
	InfrastructureTarget string      `json:"infrastructure_target"`
}

type lifecycleErrorResponse struct {
	Error  string `json:"error"`
	Status string `json:"status,omitempty"`
}

type PublicEndpointRequestDto struct {
	JobName    string `json:"job_name"`
	JobVersion string `json:"job_version"`
	Endpoint   string `json:"endpoint"`
	Active     bool   `json:"active"`
}

type NotFoundError struct {
	error
}

func (e NotFoundError) Error() string {
	return e.error.Error()
}

type LifecycleClient interface {
	AuthorizeCaller(jobName, jobVersion, endpoint string) (*JobCallAuthData, error)
}

type lifecycleClient struct {
	lifecycleUrl         string
	authToken            string
	internalToken        string
	httpClient           *http.Client
	requestTracingHeader string
	requestId            string
}

// Master Lifecycle Client makes calls to locally-available Lifecycle
func NewMasterLifecycleClient(
	lifecycleUrl string,
	authToken string,
	internalToken string,
	requestTracingHeader string,
	requestId string,
) LifecycleClient {
	return &lifecycleClient{
		lifecycleUrl:  lifecycleUrl,
		authToken:     authToken,
		internalToken: internalToken,
		httpClient: &http.Client{
			Timeout:   10 * time.Second,
			Transport: defaultLifecycleTransport,
		},
		requestTracingHeader: requestTracingHeader,
		requestId:            requestId,
	}
}

func (l *lifecycleClient) GetJobDetails(jobName string, jobVersion string) (*JobDetails, error) {
	url := JoinURL(l.lifecycleUrl, "/api/v1/job/", jobName, "/", jobVersion)
	job := &JobDetails{}
	err := l.getRequest(url, true, "getting Job details", true, job)
	if err != nil {
		return nil, err
	}
	return job, nil
}

func (l *lifecycleClient) AuthorizeCaller(jobName, jobVersion, endpoint string) (*JobCallAuthData, error) {
	url := JoinURL(l.lifecycleUrl, "/api/v1/auth/can-call-job/", jobName, "/", jobVersion, "/", endpoint)
	jobCall := &JobCallAuthData{}
	err := l.getRequest(url, false, "Authorizing Job caller", true, jobCall)
	if err != nil {
		return nil, err
	}
	return jobCall, nil
}

func (l *lifecycleClient) getRequest(
	url string,
	internalAuth bool,
	operationType string,
	decodeResponse bool,
	response interface{},
) error {
	startTime := time.Now()
	metricLifecycleCalls.Inc()

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return errors.Wrap(err, "creating GET request to Lifecycle")
	}

	if l.requestTracingHeader != "" {
		req.Header.Set(l.requestTracingHeader, l.requestId)
	}
	if internalAuth {
		req.Header.Set(AuthHeader, l.internalToken)
	} else {
		req.Header.Set(AuthHeader, l.authToken)
	}

	r, err := l.httpClient.Do(req)
	if err != nil {
		return errors.Wrap(err, "GET request to Lifecycle")
	}
	defer r.Body.Close()

	if r.StatusCode >= 400 {
		errorResp := &lifecycleErrorResponse{}
		_ = json.NewDecoder(r.Body).Decode(errorResp)
		explanation := errorResp.Error
		if errorResp.Status != "" {
			explanation += ": " + errorResp.Status
		}

		err := errors.Errorf("%s: %s", operationType, explanation)
		if r.StatusCode == http.StatusUnauthorized {
			return AuthenticationFailure{err}
		} else if r.StatusCode == http.StatusNotFound {
			return NotFoundError{err}
		}
		return err
	}

	if decodeResponse {
		err = json.NewDecoder(r.Body).Decode(response)
		if err != nil {
			return errors.Wrap(err, "JSON decoding error")
		}
	}
	metricLifecycleCallTime.Add(time.Since(startTime).Seconds())
	return nil
}

func (l *lifecycleClient) makeRequest(
	method string,
	url string,
	internalAuth bool,
	operationType string,
	decodeResponse bool,
	response interface{},
	bodyReader io.Reader,
) error {
	startTime := time.Now()
	metricLifecycleCalls.Inc()

	req, err := http.NewRequest(method, url, bodyReader)
	if err != nil {
		return errors.Wrapf(err, "creating %s request to Lifecycle", method)
	}

	if l.requestTracingHeader != "" {
		req.Header.Set(l.requestTracingHeader, l.requestId)
	}
	if internalAuth {
		req.Header.Set(AuthHeader, l.internalToken)
	} else {
		req.Header.Set(AuthHeader, l.authToken)
	}

	r, err := l.httpClient.Do(req)
	if err != nil {
		return errors.Wrapf(err, "%s request to Lifecycle", method)
	}
	defer r.Body.Close()

	if r.StatusCode >= 400 {
		errorResp := &lifecycleErrorResponse{}
		_ = json.NewDecoder(r.Body).Decode(errorResp)
		explanation := errorResp.Error
		if errorResp.Status != "" {
			explanation += ": " + errorResp.Status
		}

		err := errors.Errorf("%s: %s", operationType, explanation)
		if r.StatusCode == http.StatusUnauthorized {
			return AuthenticationFailure{err}
		} else if r.StatusCode == http.StatusNotFound {
			return NotFoundError{err}
		}
		return err
	}

	if decodeResponse {
		err = json.NewDecoder(r.Body).Decode(response)
		if err != nil {
			return errors.Wrap(err, "JSON decoding error")
		}
	}
	metricLifecycleCallTime.Add(time.Since(startTime).Seconds())
	return nil
}
