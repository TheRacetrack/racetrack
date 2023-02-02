package main

import (
	"testing"

	"github.com/jarcoal/httpmock"
	"github.com/stretchr/testify/assert"
)

func TestCheckingPublicPaths(t *testing.T) {
	httpmock.Activate()
	defer httpmock.DeactivateAndReset()

	httpmock.RegisterResponder("GET", "http://localhost:7202/lifecycle/api/v1/job/skynet/0.0.1/public-endpoints",
		httpmock.NewStringResponder(200,
			`[{"job_name": "skynet", "job_version": "0.0.1", "endpoint": "/api/v1/webview", "active": true}]`))

	lifecycleClient := NewLifecycleClient("http://localhost:7202/lifecycle", "", "secret", "traceparent", "1")

	{
		public, err := lifecycleClient.IsPathPublic("skynet", "0.0.1", "/api/v1/webview/index.html")
		assert.NoError(t, err)
		assert.True(t, public)
	}
	{
		public, err := lifecycleClient.IsPathPublic("skynet", "0.0.1", "/api/v1/webview")
		assert.NoError(t, err)
		assert.True(t, public)
	}
	{
		public, err := lifecycleClient.IsPathPublic("skynet", "0.0.1", "/api/v1/webview/")
		assert.NoError(t, err)
		assert.True(t, public)
	}
	{
		public, err := lifecycleClient.IsPathPublic("skynet", "0.0.1", "/")
		assert.NoError(t, err)
		assert.False(t, public)
	}
}
