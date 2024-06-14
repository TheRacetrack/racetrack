import collections
import threading
from typing import Iterator

import psutil
from prometheus_client import Counter, Gauge
from prometheus_client.core import REGISTRY
from prometheus_client.metrics_core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector

from lifecycle.server.db_status import database_status

metric_requested_job_deployments = Counter(
    'requested_job_deployments',
    'Number of started job deployments',
)
metric_done_job_deployments = Counter(
    'done_job_deployments',
    'Number of finished job deployments (processed or failed)',
)
metric_deployed_job = Counter('deployed_job', 'Number of Jobs deployed successfully')
metric_metrics_scrapes = Counter('metrics_scrapes', 'Number of Prometheus metrics scrapes')

metric_jobs_count_by_status = Gauge(
    "jobs_count_by_status",
    "Number of jobs with a particular status",
    labelnames=['status'],
)
metric_event_stream_client_connected = Gauge(
    "lifecycle_event_stream_client_connected",
    "Total number of successful connections to the event stream",
)
metric_event_stream_client_disconnected = Gauge(
    "lifecycle_event_stream_client_disconnected",
    "Total number of disconnections from the event stream",
)

metric_database_connection_opened = Counter(
    'lifecycle_database_connection_opened',
    'Number of attempts to open a connection to a database (successful or failed)',
)
metric_database_connection_failed = Counter(
    'lifecycle_database_connection_failed',
    'Number of times connection to a database has failed',
)
metric_database_connection_closed = Counter(
    'lifecycle_database_connection_closed',
    'Number of times connection to a database has been closed',
)
metric_database_cursor_created = Counter(
    'lifecycle_database_cursor_created',
    'Number of times database cursor has been created',
)


def setup_lifecycle_metrics():
    REGISTRY.register(ServerResourcesCollector())


def unregister_metrics():
    """
    Clean up Prometheus metrics registered by this app.
    It's important if you want to run the server more than once, eg. in tests.
    """
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)


class ServerResourcesCollector(Collector):
    def collect(self):
        metric_metrics_scrapes.inc()
        yield from collect_active_threads_metric()
        yield from collect_tcp_connections_metric()
        yield from collect_database_connection_metric()


def collect_active_threads_metric() -> Iterator[Metric]:
    metric_name = 'lifecycle_active_threads_count'
    metric_value = threading.active_count()
    prometheus_metric = GaugeMetricFamily(metric_name, 'Number of Thread objects currently alive')
    prometheus_metric.add_sample(metric_name, {}, metric_value)
    yield prometheus_metric


def collect_tcp_connections_metric() -> Iterator[Metric]:
    net_connections = psutil.net_connections(kind='tcp')
    tcp_connections = collections.Counter(conn.status for conn in net_connections)
    metric_name = 'lifecycle_tcp_connections_count'
    prometheus_metric = GaugeMetricFamily(metric_name, 'Number of open TCP connections by status')
    for status, count in tcp_connections.items():
        prometheus_metric.add_sample(metric_name, {
            'status': status,
        }, count)
    yield prometheus_metric

    remote_ports = [c.raddr.port for c in net_connections if c.status == 'ESTABLISHED' and c.raddr.port < 10000]
    established_port_conns = collections.Counter(remote_ports)
    metric_name = 'lifecycle_established_connections_count'
    prometheus_metric = GaugeMetricFamily(metric_name, 'Number of Established TCP connections by remote port (below 10000)')
    for port, count in established_port_conns.items():
        prometheus_metric.add_sample(metric_name, {
            'port': str(port),
        }, count)
    yield prometheus_metric


def collect_database_connection_metric() -> Iterator[Metric]:
    metric_name = 'lifecycle_database_connected'
    metric_value = 1 if database_status.connected else 0
    prometheus_metric = GaugeMetricFamily(metric_name, 'Status of database connection')
    prometheus_metric.add_sample(metric_name, {}, metric_value)
    yield prometheus_metric
