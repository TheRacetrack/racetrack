import socket
import os

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


class DatabaseConnectionCollector(Collector):
    def collect(self):
        metric_name = 'lifecycle_database_connected'
        metric_value = 1 if is_database_connected() else 0
        prometheus_metric = GaugeMetricFamily(metric_name, 'Status of database connection')
        prometheus_metric.add_sample(metric_name, {}, metric_value)
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
        connection.cursor().execute("select 1")
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
