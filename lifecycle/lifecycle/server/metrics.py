from django.db import connection, close_old_connections
from django.db.utils import OperationalError
from prometheus_client import Counter
from prometheus_client.core import REGISTRY
from prometheus_client.metrics_core import GaugeMetricFamily

from lifecycle.django.registry.database import db_access


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


@db_access
def is_database_connected() -> bool:
    try:
        close_old_connections()
        connection.cursor().execute("select 1")
        return True
    except OperationalError:
        return False
