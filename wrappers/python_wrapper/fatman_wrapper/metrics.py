from typing import Dict, List

from prometheus_client import Counter, Histogram, Gauge
from prometheus_client.core import REGISTRY
from prometheus_client.metrics_core import GaugeMetricFamily

from fatman_wrapper.entrypoint import FatmanEntrypoint
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)

metric_request_internal_errors = Counter(
    'request_internal_errors',
    'Number of server errors when calling a Fatman',
    labelnames=['endpoint'],
)
metric_request_duration = Histogram(
    'request_duration',
    'Duration of model call',
    buckets=(.001, .0025, .005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5,
             10.0, 25.0, 50.0, 75.0, 100.0, 250.0, 500.0, 750.0, 1000.0, float("inf")),
    labelnames=['endpoint'],
)
metric_requests_started = Counter(
    'requests_started',
    'Total number of started requests calling Fatman (may be not finished yet)',
)
metric_requests_done = Counter(
    'requests_done',
    'Total number of finished requests calling Fatman (processed and done)',
)
metric_endpoint_requests_started = Counter(
    'endpoint_requests_started',
    'Total number of started requests calling Fatman (may be not finished yet)',
    labelnames=['endpoint'],
)
metric_last_call_timestamp = Gauge(
    'last_call_timestamp',
    'Timestamp (in seconds) of the last request calling Fatman',
)


def setup_entrypoint_metrics(entrypoint: FatmanEntrypoint):
    if not hasattr(entrypoint, 'metrics'):
        return
    metrics_function = getattr(entrypoint, 'metrics')
    REGISTRY.register(FatmanMetricsCollector(metrics_function))


class FatmanMetricsCollector:
    def __init__(self, metrics_function):
        self._metrics_function = metrics_function

    def collect(self):
        metrics: List[Dict] = self._metrics_function()
        for metric in metrics:
            name = metric.get('name')
            description = metric.get('description', '')
            labels = metric.get('labels', {})
            if not name:
                logger.error('"name" field is undefined for one of the metrics')
                continue
            if 'value' not in metric:
                logger.error(f'"value" field is undefined for {name} metric')
                continue
            value = metric['value']
            if value is None:
                continue

            prometheus_metric = GaugeMetricFamily(name, description)
            prometheus_metric.add_sample(name, labels, value)
            yield prometheus_metric
