package main

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	metricFatmanProxyRequests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_fatman_proxy_requests",
		Help: "Total number of incoming requests accessing Fatman proxy (may be unfinished, successful or erroneous)",
	}, []string{"fatman_name", "fatman_version"})
	metricFatmanProxyRequestsStarted = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_fatman_proxy_requests_started",
		Help: "Total number of started requests accessing Fatman proxy (may be unfinished yet or successful)",
	}, []string{"fatman_name", "fatman_version"})
	metricFatmanProxyRequestsDone = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_fatman_proxy_requests_done",
		Help: "Total number of finished requests to Fatman proxy (done)",
	}, []string{"fatman_name", "fatman_version"})
	metricFatmanProxyResponseCodes = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_fatman_proxy_response_codes",
		Help: "Number of Fatman proxy responses with a particular HTTP status code",
	}, []string{"fatman_name", "fatman_version", "status_code"})
	metricFatmanProxyErrors = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_fatman_proxy_errors",
		Help: "Total number of failures when accessing Fatman proxy (failure of PUB itself)",
	})
	metricFatmanProxyRequestErrors = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_fatman_proxy_request_errors",
		Help: "Total number of proxy request failures caused by bad requests",
	})
	metricFatmanCallResponseTime = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "pub_fatman_call_response_time",
		Help: "Total number of seconds spent waiting for a fatman to answer a call",
	}, []string{"fatman_name", "fatman_version"})
	metricOverallFatmanProxyResponseTime = promauto.NewCounter(prometheus.CounterOpts{
		Name: "pub_overall_fatman_proxy_response_time",
		Help: "Total duration of overall Fatman proxy requests handling (sum of seconds)",
	})
	metricFatmanCallResponseTimeHistogram = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "pub_fatman_call_response_time_histogram",
		Help:    "Response time of a forwarded fatman call",
		Buckets: prometheus.ExponentialBuckets(0.001, 2, 21),
	}, []string{"fatman_name", "fatman_version"})

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
)
