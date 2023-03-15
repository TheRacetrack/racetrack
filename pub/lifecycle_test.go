package main

import (
	"testing"

	"github.com/jarcoal/httpmock"
	"github.com/stretchr/testify/assert"
)

func TestAuthorizeCaller(t *testing.T) {
	httpmock.Activate()
	defer httpmock.DeactivateAndReset()

	httpmock.RegisterResponder("GET", "http://localhost:7202/lifecycle/api/v1/auth/can-call-job/skynet/latest",
		httpmock.NewStringResponder(200,
			`{"id": "000", "name": "skynet", "version": "0.0.1", "status": "running", "create_time": 1000, "update_time": 1000, "manifest": null, "internal_name": "adder-v-0-0-1"}`))

	httpmock.RegisterResponder("GET", "http://localhost:7202/lifecycle/api/v1/auth/can-call-job/skynet/0.0.1/api/v1/perform",
		httpmock.NewStringResponder(200,
			`{"id": "000", "name": "skynet", "version": "0.0.1", "status": "running", "create_time": 1000, "update_time": 1000, "manifest": null, "internal_name": "adder-v-0-0-1"}`))

	httpmock.RegisterResponder("GET", "http://localhost:7202/lifecycle/api/v1/auth/can-call-job/typo/0.0.1/api/v1/perform",
		httpmock.NewStringResponder(404,
			`{"error": "Job typo was not found"}`))
	httpmock.RegisterResponder("GET", "http://localhost:7202/lifecycle/api/v1/auth/can-call-job/secret/0.0.1/api/v1/perform",
		httpmock.NewStringResponder(401,
			`{"error": "You have no power here"}`))

	lifecycleClient := NewLifecycleClient("http://localhost:7202/lifecycle", "", "secret", "traceparent", "1")

	{
		job, err := lifecycleClient.AuthorizeCaller("skynet", "latest", "")
		assert.NoError(t, err)
		assert.Equal(t, "skynet", job.Name)
		assert.Equal(t, "0.0.1", job.Version)
		assert.Equal(t, "running", job.Status)
		assert.Equal(t, 1000, job.UpdateTime)
		assert.Equal(t, "adder-v-0-0-1", job.InternalName)
	}
	{
		job, err := lifecycleClient.AuthorizeCaller("skynet", "0.0.1", "/api/v1/perform")
		assert.NoError(t, err)
		assert.Equal(t, "adder-v-0-0-1", job.InternalName)
	}
	{
		job, err := lifecycleClient.AuthorizeCaller("typo", "0.0.1", "/api/v1/perform")
		assert.EqualError(t, err, "Authorizing Job caller: Job typo was not found")
		assert.Nil(t, job)
	}
	{
		job, err := lifecycleClient.AuthorizeCaller("secret", "0.0.1", "/api/v1/perform")
		assert.EqualError(t, err, "Authorizing Job caller: You have no power here")
		assert.Nil(t, job)
	}
}
