package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/pkg/errors"
)

type JobDetails struct {
	Id           string      `json:"id"`
	Name         string      `json:"name"`
	Version      string      `json:"version"`
	Status       string      `json:"status"`
	CreateTime   int         `json:"create_time"`
	UpdateTime   int         `json:"update_time"`
	Manifest     interface{} `json:"manifest"`
	InternalName string      `json:"internal_name"`
}

type lifecycleErrorResponse struct {
	Error  string `json:"error"`
	Status string `json:"status,omitempty"`
}

type PublicEndpointRequestDto struct {
	JobName    string `json:"job.name"`
	JobVersion string `json:"job.version"`
	Endpoint      string `json:"endpoint"`
	Active        bool   `json:"active"`
}

var JobNotFound = errors.New("job was not found")

type LifecycleClient struct {
	lifecycleUrl         string
	authToken            string
	internalToken        string
	httpClient           *http.Client
	requestTracingHeader string
	requestId            string
}

const AuthScopeCallJob = "call_fatman"

func NewLifecycleClient(
	lifecycleUrl string,
	authToken string,
	internalToken string,
	requestTracingHeader string,
	requestId string,
) *LifecycleClient {
	return &LifecycleClient{
		lifecycleUrl:  lifecycleUrl,
		authToken:     authToken,
		internalToken: internalToken,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
		requestTracingHeader: requestTracingHeader,
		requestId:            requestId,
	}
}

func (l *LifecycleClient) GetJobDetails(jobName string, jobVersion string) (*JobDetails, error) {
	url := JoinURL(l.lifecycleUrl, "/api/v1/job/", jobName, "/", jobVersion)
	job := &JobDetails{}
	err := l.getRequest(url, true, "getting Job details", true, job)
	if err != nil {
		return nil, err
	}
	return job, nil
}

func (l *LifecycleClient) HasAccessToJob(jobName, jobVersion string, scope string) (bool, error) {
	url := JoinURL(l.lifecycleUrl, "/api/v1/auth/allowed/job/", jobName, "/", jobVersion, "/scope/", scope)
	err := l.getRequest(url, false, "checking access to call Job", false, nil)
	if err != nil {
		return false, err
	}
	return true, nil
}

func (l *LifecycleClient) HasAccessToJobEndpoint(jobName, jobVersion, endpoint string) (bool, error) {
	url := JoinURL(l.lifecycleUrl, "/api/v1/auth/allowed/job_endpoint/", jobName, "/", jobVersion, "/scope/", AuthScopeCallJob, "/endpoint/", endpoint)
	err := l.getRequest(url, false, "checking access to call Job endpoint", false, nil)
	if err != nil {
		return false, err
	}
	return true, nil
}

func (l *LifecycleClient) GetJobPublicEndpoints(jobName, jobVersion string) ([]string, error) {
	url := JoinURL(l.lifecycleUrl, "/api/v1/job/", jobName, "/", jobVersion, "/public-endpoints")
	result := []*PublicEndpointRequestDto{}
	err := l.getRequest(url, true, "getting Job public endpoints", true, &result)
	if err != nil {
		return nil, err
	}

	publicPaths := []string{}
	for _, dto := range result {
		if dto.Active {
			publicPaths = append(publicPaths, dto.Endpoint)
		}
	}

	return publicPaths, nil
}

func (l *LifecycleClient) IsPathPublic(jobName, jobVersion, jobPath string) (bool, error) {
	publicPaths, err := l.GetJobPublicEndpoints(jobName, jobVersion)
	if err != nil {
		return false, err
	}

	for _, publicPath := range publicPaths {
		if strings.HasPrefix(jobPath, publicPath) {
			return true, nil
		}
	}

	return false, nil
}

func (l *LifecycleClient) AuthenticateCaller(path, jobName, jobVersion, jobPath string, debug bool) error {
	for _, unprotectedEndpoint := range unprotectedEndpoints {
		if strings.HasPrefix(jobPath, unprotectedEndpoint) {
			return nil
		}
	}

	public, err := l.IsPathPublic(jobName, jobVersion, jobPath)
	if err != nil {
		return errors.Wrap(err, "checking public paths")
	}
	if public {
		return nil
	}

	if l.authToken == "" {
		return AuthFailure(
			errors.New("not logged in"),
			fmt.Sprintf("empty header value of %s", AuthHeader),
			debug,
		)
	}

	ok, err := l.HasAccessToJobEndpoint(jobName, jobVersion, jobPath)
	if err != nil {
		return errors.Wrap(err, "Auth error")
	}
	if !ok {
		return AuthFailure(nil, "Unauthorized to access this job", debug)
	}
	return nil
}

func (l *LifecycleClient) getRequest(
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

	if r.StatusCode == http.StatusNotFound {
		return JobNotFound
	}
	if r.StatusCode >= 400 {
		errorResp := &lifecycleErrorResponse{}
		_ = json.NewDecoder(r.Body).Decode(errorResp)
		explanation := errorResp.Error
		if errorResp.Status != "" {
			explanation += ": " + errorResp.Status
		}

		err := errors.Errorf("%s: %s response from Lifecycle: %s", operationType, r.Status, explanation)
		if r.StatusCode == 401 {
			return AuthenticationFailure{err}
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
