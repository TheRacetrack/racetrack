package main

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"os"

	"github.com/gorilla/mux"
	log "github.com/inconshreveable/log15"
	"github.com/pkg/errors"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/sdk/resource"
	"go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.12.0"
)

var tracer = otel.Tracer("github.com/TheRacetrack/racetrack/pub")

var telemetryExcludedEndpoints = map[string]bool{
	"GET /metrics": true,
	"GET /health":  true,
	"GET /live":    true,
	"GET /ready":   true,
}

func SetupOpenTelemetry(router *mux.Router, cfg *Config) (*trace.TracerProvider, error) {
	otlpEndpoint := cfg.OpenTelemetryEndpoint
	otlpUrl, err := url.Parse(otlpEndpoint)
	if err != nil {
		return nil, errors.Wrap(err, "Invalid OTLP endpoint URL")
	}
	var otlpOptions []otlptracehttp.Option = []otlptracehttp.Option{
		otlptracehttp.WithEndpoint(otlpUrl.Host),
		otlptracehttp.WithURLPath(otlpUrl.Path),
	}
	if otlpUrl.Scheme == "http" {
		otlpOptions = append(otlpOptions, otlptracehttp.WithInsecure())
	}

	exporter, err := otlptracehttp.New(
		context.Background(),
		otlpOptions...,
	)
	if err != nil {
		log.Error("Creating Open Telemetry exporter", log.Ctx{"error": err})
	}

	tp := trace.NewTracerProvider(
		trace.WithBatcher(exporter),
		trace.WithResource(newResource(cfg)),
	)
	otel.SetTracerProvider(tp)

	telemetryMiddleware := func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {

			endpointName := fmt.Sprintf("%s %s", req.Method, req.URL.Path)
			_, isExcluded := telemetryExcludedEndpoints[endpointName]

			if !isExcluded {
				_, span := tracer.Start(context.Background(), endpointName)

				traceparent := req.Header.Get(cfg.RequestTracingHeader)
				if traceparent == "" {
					traceId := span.SpanContext().TraceID().String()
					spanId := span.SpanContext().SpanID().String()
					traceparent = fmt.Sprintf("00-%s-%s-01", traceId, spanId)
					req.Header.Set(cfg.RequestTracingHeader, traceparent)
				}

				span.SetAttributes(
					attribute.String("endpoint.method", req.Method),
					attribute.String("endpoint.path", req.URL.Path),
					attribute.String("traceparent", traceparent),
				)
				defer span.End()
			}

			next.ServeHTTP(w, req)
		})
	}

	router.Use(telemetryMiddleware)
	log.Info("OpenTelemetry traces are enabled", log.Ctx{"endpoint": cfg.OpenTelemetryEndpoint})

	return tp, nil
}

func newResource(cfg *Config) *resource.Resource {
	deploymentEnvironment := os.Getenv("SITE_NAME")
	clusterHostname := os.Getenv("CLUSTER_FQDN")

	r, _ := resource.Merge(
		resource.Default(),
		resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceNameKey.String("pub"),
			semconv.ServiceVersionKey.String(cfg.GitVersion),
			semconv.DeploymentEnvironmentKey.String(deploymentEnvironment),
			attribute.String("cluster_hostname", clusterHostname),
		),
	)
	return r
}
