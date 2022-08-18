import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, DEPLOYMENT_ENVIRONMENT, SERVICE_NAMESPACE, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from lifecycle.config.config import Config


def setup_opentelemetry(config: Config):
    git_version = os.environ.get('GIT_VERSION')
    docker_tag = os.environ.get('DOCKER_TAG')
    racetrack_version = f"{docker_tag} ({git_version})"

    resource = Resource(attributes={
        DEPLOYMENT_ENVIRONMENT: os.environ.get('SITE_NAME', 'dev'),
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
