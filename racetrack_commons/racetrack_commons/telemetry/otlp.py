import os
import re
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAMESPACE, SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.span import SpanContext

from racetrack_commons.api.tracing import get_tracing_header_name
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)

EXCLUDED_ENDPOINTS = {
	"GET /metrics",
	"GET /health",
	"GET /live",
	"GET /ready",
}

traceparent_pattern = re.compile(r'00-(?P<trace_id>[0-9a-f]+)-(?P<span_id>[0-9a-f]+)-(?P<trace_flags>[0-9a-f]+)')


def setup_opentelemetry(
    fastapi_app: FastAPI,
    open_telemetry_endpoint: str,
    service_name: str,
    attributes: Dict[str, str],
):
    git_version = os.environ.get('GIT_VERSION')
    docker_tag = os.environ.get('DOCKER_TAG')
    racetrack_version = f"{docker_tag} ({git_version})"

    resource = Resource(attributes={
        DEPLOYMENT_ENVIRONMENT: os.environ.get('SITE_NAME', 'local'),
        SERVICE_NAMESPACE: 'racetrack',
        SERVICE_NAME: service_name,
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

    tracer = trace.get_tracer(__name__)
    tracing_header = get_tracing_header_name()

    @fastapi_app.middleware('http')
    async def otlp_tracer(request: Request, call_next) -> Response:
        endpoint_name = f'{request.method} {request.url.path}'
        if endpoint_name in EXCLUDED_ENDPOINTS:
            return await call_next(request)
        else:
            traceparent = request.headers.get(tracing_header)

            parent_ctx = _get_span_parent_context(traceparent)
            span_links = [trace.Link(parent_ctx)] if parent_ctx is not None else []

            with tracer.start_as_current_span(endpoint_name, links=span_links) as span:
                span.set_attribute('endpoint.method', request.method)
                span.set_attribute('endpoint.path', request.url.path)
                if traceparent:
                    span.set_attribute('traceparent', traceparent)
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


def _get_span_parent_context(traceparent: str) -> Optional[SpanContext]:
    if not traceparent:
        return None

    match = traceparent_pattern.fullmatch(traceparent)
    if not match:
        return None
    
    trace_id_int = int(match.group('trace_id'), 16)
    span_id_int = int(match.group('span_id'), 16)
    return SpanContext(trace_id=trace_id_int, span_id=span_id_int, is_remote=True)
