import collections
import threading
from typing import Iterator

import psutil
from prometheus_client.core import REGISTRY
from prometheus_client.metrics_core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector

from lifecycle.server.cache import LifecycleCache
from lifecycle.server.metrics import metric_metrics_scrapes


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

    max_remote_port = 10000
    remote_ports = [c.raddr.port for c in net_connections if c.status == 'ESTABLISHED' and c.raddr.port < max_remote_port]
    established_port_conns = collections.Counter(remote_ports)
    metric_name = 'lifecycle_established_connections_count'
    prometheus_metric = GaugeMetricFamily(
        metric_name,
        f'Number of Established TCP connections by remote port (below {max_remote_port})',
    )
    for port, count in established_port_conns.items():
        prometheus_metric.add_sample(metric_name, {
            'port': str(port),
        }, count)
    yield prometheus_metric


def collect_database_connection_metric() -> Iterator[Metric]:
    database_status = LifecycleCache.db_engine().database_status()

    if database_status.connected is not None:
        metric_value = 1 if database_status.connected is True else 0
        yield make_metric_sample(
            'lifecycle_database_connected',
            'Status of database connection',
            metric_value)

    yield make_metric_sample(
        'lifecycle_database_pool_size',
        'Number of connections currently managed by the pool (in the pool, given to clients, being prepared)',
        database_status.pool_size)
    yield make_metric_sample(
        'lifecycle_database_pool_available',
        'Number of connections currently idle in the pool',
        database_status.pool_available)
    yield make_metric_sample(
        'lifecycle_database_requests_waiting',
        'Number of requests currently waiting in a queue to receive a connection',
        database_status.requests_waiting)
    yield make_metric_sample(
        'lifecycle_database_usage_ms',
        'Total usage time of the connections outside the pool',
        database_status.usage_ms)
    yield make_metric_sample(
        'lifecycle_database_requests_num',
        'Number of connections requested to the pool',
        database_status.requests_num)
    yield make_metric_sample(
        'lifecycle_database_requests_queued',
        'Number of requests queued because a connection wasn’t immediately available in the pool',
        database_status.requests_queued)
    yield make_metric_sample(
        'lifecycle_database_requests_wait_ms',
        'Total time in the queue for the clients waiting',
        database_status.requests_wait_ms)
    yield make_metric_sample(
        'lifecycle_database_requests_errors',
        'Number of connection requests resulting in an error (timeouts, queue full)',
        database_status.requests_errors)
    yield make_metric_sample(
        'lifecycle_database_connections_num',
        'Number of connection attempts made by the pool to the server',
        database_status.connections_num)
    yield make_metric_sample(
        'lifecycle_database_connections_ms',
        'Total time spent to establish connections with the server',
        database_status.connections_ms)
    yield make_metric_sample(
        'lifecycle_database_connections_errors',
        'Number of failed connection attempts',
        database_status.connections_errors)


def make_metric_sample(metric_name: str, description: str, value: float) -> GaugeMetricFamily:
    prometheus_metric = GaugeMetricFamily(metric_name, description)
    prometheus_metric.add_sample(metric_name, {}, value)
    return prometheus_metric
