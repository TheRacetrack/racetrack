package main

import (
	"context"
	"net/http"
	"os"

	"github.com/gorilla/mux"
	log "github.com/inconshreveable/log15"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/sdk/resource"
	"go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.12.0"
)

var tracer = otel.Tracer("github.com/TheRacetrack/racetrack/pub")

func SetupOpenTelemetry(router *mux.Router, cfg *Config) *trace.TracerProvider {
	exporter, err := otlptracehttp.New(
		context.Background(),
		otlptracehttp.WithEndpoint("host.docker.internal:4318"), // TODO split
		otlptracehttp.WithURLPath("/v1/traces"),
		otlptracehttp.WithInsecure(),
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
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

			requestId := getRequestTracingId(r, cfg.RequestTracingHeader)
			_, span := tracer.Start(context.Background(), "pub-trace")
			span.SetAttributes(
				attribute.String("endpoint.method", r.Method),
				attribute.String("endpoint.path", r.URL.Path),
				attribute.String("request_tracing_id", requestId),
			)
			defer span.End()

			next.ServeHTTP(w, r)
		})
	}

	router.Use(telemetryMiddleware)
	log.Info("OpenTelemetry traces configured", log.Ctx{"endpoint": cfg.OpenTelemetryEndpoint})

	return tp
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
