import collections
import os
import threading
from typing import Iterator

import psutil
from django.conf import settings
from django.db import connection, close_old_connections
from django.db.utils import OperationalError
from prometheus_client import Counter, Gauge
from prometheus_client.core import REGISTRY
from prometheus_client.registry import Collector
from prometheus_client.metrics_core import GaugeMetricFamily, Metric

from racetrack_client.utils.shell import CommandError, shell

metric_requested_job_deployments = Counter('requested_job_deployments', 'Number of requests to deploy job')
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
    metric_name = 'lifecycle_tcp_connections_count'
    tcp_connections = collections.Counter(p.status for p in psutil.net_connections(kind='tcp'))
    prometheus_metric = GaugeMetricFamily(metric_name, 'Number of open TCP connections by status')
    for status, count in tcp_connections.items():
        prometheus_metric.add_sample(metric_name, {
            'status': status,
        }, count)
    yield prometheus_metric


def collect_database_connection_metric() -> Iterator[Metric]:
    metric_name = 'lifecycle_database_connected'
    metric_value = 1 if is_database_connected() else 0
    prometheus_metric = GaugeMetricFamily(metric_name, 'Status of database connection')
    prometheus_metric.add_sample(metric_name, {}, metric_value)
    yield prometheus_metric


def is_database_connected() -> bool:
    try:
        django_db_type = os.environ.get('DJANGO_DB_TYPE', 'sqlite')
        if django_db_type == 'postgres':
            db_name = settings.DATABASES['default']['NAME']
            user = settings.DATABASES['default']['USER']
            host = settings.DATABASES['default']['HOST']
            port = settings.DATABASES['default']['PORT']
            # raise CommandError on non-zero exit code.
            shell(f'pg_isready -h {host} -p {port} -U {user} -d {db_name}', print_stdout=False)
        else:
            close_old_connections()
            with connection.cursor() as cursor:
                cursor.execute('select 1')
        return True
    except CommandError:
        return False
    except OperationalError:
        return False
