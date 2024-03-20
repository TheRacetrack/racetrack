package main

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	metricJobProxyRequests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_job_proxy_requests",
		Help: "Total number of incoming requests accessing Job proxy (may be unfinished, successful or erroneous)",
	}, []string{"job_name", "job_version"})
	metricJobProxyRequestsStarted = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_job_proxy_requests_started",
		Help: "Total number of started requests accessing Job proxy (may be unfinished yet or successful)",
	}, []string{"job_name", "job_version"})
	metricJobProxyRequestsDone = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_job_proxy_requests_done",
		Help: "Total number of finished requests to Job proxy (done)",
	}, []string{"job_name", "job_version"})
	metricJobProxyResponseCodes = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_job_proxy_response_codes",
		Help: "Number of Job proxy responses with a particular HTTP status code",
	}, []string{"job_name", "job_version", "status_code"})
	metricJobProxyErrors = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_job_proxy_errors",
		Help: "Total number of failures when accessing Job proxy (failure of PUB itself)",
	})
	metricJobProxyRequestErros = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_job_proxy_request_errors",
		Help: "Total number of proxy request failures caused by bad requests",
	})
	metricJobCallResponseTime = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_job_call_response_time",
		Help: "Total number of seconds spent waiting for a Job to answer a call",
	}, []string{"job_name", "job_version"})
	metricOverallJobProxyResponseTime = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_overall_job_proxy_response_time",
		Help: "Total duration of overall Job proxy requests handling (sum of seconds)",
	})
	metricJobCallResponseTimeHistogram = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "pub_job_call_response_time_histogram",
		Help:    "Response time of a forwarded Job call",
		Buckets: prometheus.ExponentialBuckets(0.001, 2, 21),
	}, []string{"job_name", "job_version"})

	metricHealthRequests = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_health_requests",
		Help: "Total number of health-check requests",
	})

	metricLifecycleCalls = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_lifecycle_calls",
		Help: "Total number of calls made to Lifecycle component",
	})
	metricLifecycleCallTime = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_lifecycle_call_time",
		Help: "Total number of seconds spent on Lifecycle calls",
	})

	metricAuthSuccessful = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_auth_successful",
		Help: "Total number of successful authentication attempts",
	})
	metricAuthFailed = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_auth_failed",
		Help: "Total number of failed authentication attempts",
	})

	metricAsyncJobCallsStarted = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_async_job_calls_started",
		Help: "Total number of started async Job calls (may be unfinished yet or successful)",
	}, []string{"job_name", "job_version"})
	metricAsyncJobCallsDone = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_async_job_calls_done",
		Help: "Total number of finished async Job calls (done and successful)",
	}, []string{"job_name", "job_version"})
	metricAsyncJobCallsErrors = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_async_job_calls_errors",
		Help: "Total number of failed async Job calls",
	})
	metricAsyncRetriedTask = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_async_retried_task",
		Help: "Total number of retried async tasks",
	})
	metricAsyncRetriedCrashedTask = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_async_retried_crashed_task",
		Help: "Total number of retried async tasks due to a job crash",
	})
	metricAsyncRetriedMissingTask = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_async_retried_missing_task",
		Help: "Total number of retried async tasks due to a missing task",
	})
)
