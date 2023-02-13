import socket
import os

from django.conf import settings
from django.db import connection, close_old_connections
from django.db.utils import OperationalError
from prometheus_client import Counter
from prometheus_client.core import REGISTRY
from prometheus_client.metrics_core import GaugeMetricFamily


metric_requested_fatman_deployments = Counter('requested_fatman_deployments', 'Number of requests to deploy fatman')
metric_deployed_fatman = Counter('deployed_fatman', 'Number of Fatman deployed successfully')


def setup_lifecycle_metrics():
    REGISTRY.register(DatabaseConnectionCollector())


class DatabaseConnectionCollector:
    def collect(self):
        metric_name = 'lifecycle_database_connected'
        metric_value = 1 if is_database_connected() else 0
        prometheus_metric = GaugeMetricFamily(metric_name, 'Status of database connection')
        prometheus_metric.add_sample(metric_name, {}, metric_value)
        yield prometheus_metric


def is_database_connected() -> bool:
    try:
        DJANGO_DB_TYPE = os.environ.get('DJANGO_DB_TYPE', 'sqlite')
        if DJANGO_DB_TYPE == 'postgres':
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
