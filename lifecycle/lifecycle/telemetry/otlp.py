import os

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, DEPLOYMENT_ENVIRONMENT, SERVICE_NAMESPACE, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from lifecycle.config.config import Config
from racetrack_commons.api.tracing import get_tracing_header_name
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def setup_opentelemetry(fastapi_app: FastAPI, config: Config):
    git_version = os.environ.get('GIT_VERSION')
    docker_tag = os.environ.get('DOCKER_TAG')
    racetrack_version = f"{docker_tag} ({git_version})"

    resource = Resource(attributes={
        DEPLOYMENT_ENVIRONMENT: os.environ.get('SITE_NAME', 'dev'),
        SERVICE_NAMESPACE: 'racetrack',
        SERVICE_NAME: config.open_telemetry_service_name,
        SERVICE_VERSION: racetrack_version,
    })

    provider = TracerProvider(resource=resource)
    if config.open_telemetry_endpoint == 'console':
        exporter = ConsoleSpanExporter()
    else:
        exporter = OTLPSpanExporter(endpoint=config.open_telemetry_endpoint)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    tracer = trace.get_tracer(__name__)

    tracing_header = get_tracing_header_name()

    @fastapi_app.middleware('http')
    async def otlp_tracer(request: Request, call_next) -> Response:
        with tracer.start_as_current_span("lifecycle-span") as span:
            tracing_id = request.headers.get(tracing_header)
            span.set_attribute('endpoint.method', request.method)
            span.set_attribute('endpoint.path', request.url.path)
            span.set_attribute('tracing_id', tracing_id)
            span.set_attribute(tracing_header, tracing_id)
            span.set_attribute('cluster_hostname', os.environ.get('CLUSTER_FQDN'))
            return await call_next(request)
