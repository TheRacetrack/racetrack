import socket
import os
import threading
import collections

import psutil
from django.conf import settings
from django.db import connection, close_old_connections
from django.db.utils import OperationalError
from prometheus_client import Counter, Gauge
from prometheus_client.core import REGISTRY
from prometheus_client.registry import Collector
from prometheus_client.metrics_core import GaugeMetricFamily

metric_requested_job_deployments = Counter('requested_job_deployments', 'Number of requests to deploy job')
metric_deployed_job = Counter('deployed_job', 'Number of Jobs deployed successfully')

metric_jobs_count_by_status = Gauge(
    "jobs_count_by_status",
    "Number of jobs with a particular status",
    labelnames=['status'],
)


def setup_lifecycle_metrics():
    REGISTRY.register(DatabaseConnectionCollector())
    REGISTRY.register(ServerResourcesCollector())


def unregister_metrics():
    """
    Clean up Prometheus metrics registered by this app.
    It's important if you want to run the server more than once, eg. in tests.
    """
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)


class DatabaseConnectionCollector(Collector):
    def collect(self):
        metric_name = 'lifecycle_database_connected'
        metric_value = 1 if is_database_connected() else 0
        prometheus_metric = GaugeMetricFamily(metric_name, 'Status of database connection')
        prometheus_metric.add_sample(metric_name, {}, metric_value)
        yield prometheus_metric


class ServerResourcesCollector(Collector):
    def collect(self):
        metric_name = 'lifecycle_active_threads_count'
        metric_value = threading.active_count()
        prometheus_metric = GaugeMetricFamily(metric_name, 'Number of Thread objects currently alive')
        prometheus_metric.add_sample(metric_name, {}, metric_value)
        yield prometheus_metric

        metric_name = 'lifecycle_tcp_connections_count'
        tcp_connections = collections.Counter(p.status for p in psutil.net_connections(kind='tcp'))
        for status, count in tcp_connections.items():
            prometheus_metric = GaugeMetricFamily(metric_name, 'Number of open TCP connections by status')
            prometheus_metric.add_sample(metric_name, {
                'status': status,
            }, count)
            yield prometheus_metric


def is_database_connected() -> bool:
    try:
        django_db_type = os.environ.get('DJANGO_DB_TYPE', 'sqlite')
        if django_db_type == 'postgres':
            host = settings.DATABASES['default']['HOST']
            port = settings.DATABASES['default']['PORT']
            if not is_port_open(host, int(port)):
                return False

        close_old_connections()
        with connection.cursor() as cursor:
            cursor.execute('select 1')
            cursor.fetchone()
            cursor.close()
        connection.close()
        return True
    except OperationalError:
        return False


def is_port_open(ip: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        s.connect((ip, port))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except:
        return False
