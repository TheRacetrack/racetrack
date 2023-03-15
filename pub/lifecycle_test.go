package main

import (
	"testing"

	"github.com/jarcoal/httpmock"
	"github.com/stretchr/testify/assert"
)

func TestAuthenticateCaller(t *testing.T) {
	httpmock.Activate()
	defer httpmock.DeactivateAndReset()

	httpmock.RegisterResponder("GET", "http://localhost:7202/lifecycle/api/v1/auth/can-call-job/skynet/latest",
		httpmock.NewStringResponder(200,
			`{"id": "000", "name": "skynet", "version": "0.0.1", "status": "running", "create_time": 1000, "update_time": 1000, "manifest": null, "internal_name": "adder-v-0-0-1"}`))

	lifecycleClient := NewLifecycleClient("http://localhost:7202/lifecycle", "", "secret", "traceparent", "1")

	{
		job, err := lifecycleClient.AuthenticateCaller("skynet", "latest", "")
		assert.NoError(t, err)
		assert.Equal(t, "000", job.Id)
		assert.Equal(t, "skynet", job.Name)
		assert.Equal(t, "0.0.1", job.Version)
		assert.Equal(t, "running", job.Status)
		assert.Equal(t, 1000, job.CreateTime)
		assert.Equal(t, 1000, job.UpdateTime)
		assert.Equal(t, "adder-v-0-0-1", job.InternalName)
	}
}
