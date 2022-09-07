import os
from typing import Dict

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAMESPACE, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation import set_span_in_context
from opentelemetry.trace.span import SpanContext
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from racetrack_commons.api.tracing import get_tracing_header_name
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def setup_opentelemetry(fastapi_app: FastAPI, open_telemetry_endpoint: str, attributes: Dict[str, str]):
    git_version = os.environ.get('GIT_VERSION')
    docker_tag = os.environ.get('DOCKER_TAG')
    racetrack_version = f"{docker_tag} ({git_version})"

    resource = Resource(attributes={
        DEPLOYMENT_ENVIRONMENT: os.environ.get('SITE_NAME', 'local'),
        SERVICE_NAMESPACE: 'racetrack',
        SERVICE_VERSION: racetrack_version,
        'cluster_hostname': os.environ.get('CLUSTER_FQDN', 'local'),
        **attributes,
    })

    provider = TracerProvider(resource=resource)
    if open_telemetry_endpoint == 'console':
        exporter = ConsoleSpanExporter()
    else:
        exporter = OTLPSpanExporter(endpoint=open_telemetry_endpoint)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # https://opentelemetry.io/docs/concepts/sdk-configuration/otlp-exporter-configuration/
    # os.environ['OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'] = open_telemetry_endpoint
    # os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = open_telemetry_endpoint
    # os.environ['OTEL_EXPORTER_OTLP_PROTOCOL'] = 'http/protobuf'

    # FastAPIInstrumentor.instrument_app(fastapi_app)

    tracer = trace.get_tracer(__name__)
    tracing_header = get_tracing_header_name()

    @fastapi_app.middleware('http')
    async def otlp_tracer(request: Request, call_next) -> Response:
        span_name = f'{request.method} {request.url.path}'
        tracing_id = request.headers.get(tracing_header)

        # parent_span = tracer.start_span(span_name)
        # parent_span_id = parent_span.context.span_id
        parent_span_id = 100
        parent_span_ctx = SpanContext(trace_id=0, span_id=parent_span_id, is_remote=True)

        with tracer.start_as_current_span(span_name) as span:
            span._parent = parent_span_ctx
            span.set_attribute('endpoint.method', request.method)
            span.set_attribute('endpoint.path', request.url.path)
            span.set_attribute('tracing_id', tracing_id)
            try:
                response: Response = await call_next(request)
                span.set_attribute('response_code', response.status_code)
                span.set_status(Status(StatusCode.OK))
                return response
            except Exception as ex:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(ex)
                raise ex

    logger.info(f'OpenTelemetry traces will be sent to {open_telemetry_endpoint}')
