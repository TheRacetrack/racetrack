from typing import Optional, Iterable

from prometheus_client.parser import text_string_to_metric_families
from prometheus_client import Metric

from racetrack_client.utils.request import Requests


METRIC_LAST_CALL_TIMESTAMP = 'last_call_timestamp'


def scrape_metrics(metrics_url: str) -> Iterable[Metric]:
    response = Requests.get(metrics_url)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    content = response.content.decode('utf-8', 'strict')
    return text_string_to_metric_families(content)


def read_last_call_timestamp_metric(metrics: Iterable[Metric]) -> Optional[float]:
    for family in metrics:
        for sample in family.samples:
            if sample.name == METRIC_LAST_CALL_TIMESTAMP:
                return sample.value
    return None
