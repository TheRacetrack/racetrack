from typing import Callable, Iterable

from kubernetes import client
from kubernetes.client import V1ObjectMeta, ApiException

from lifecycle.config import Config
from lifecycle.monitor.base import FatmanMonitor
from lifecycle.monitor.health import check_until_fatman_is_operational, quick_check_fatman_condition
from lifecycle.monitor.kubernetes.utils import k8s_api_client, K8S_FATMAN_NAME_LABEL, \
    K8S_FATMAN_VERSION_LABEL, K8S_NAMESPACE, K8S_FATMAN_RESOURCE_LABEL, get_fatman_deployments, get_fatman_pods
from lifecycle.monitor.metric_parser import read_last_call_timestamp_metric, scrape_metrics
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.exception import short_exception_details
from racetrack_client.utils.shell import CommandError, shell_output
from racetrack_client.utils.time import datetime_to_timestamp
from racetrack_commons.deploy.resource import fatman_resource_name, fatman_internal_name
from racetrack_commons.entities.dto import FatmanDto, FatmanStatus
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class KubernetesMonitor(FatmanMonitor):
    """Discovers Fatmen resources in a k8s cluster and monitors their condition"""

    def list_fatmen(self, config: Config) -> Iterable[FatmanDto]:
        # Ideally these should be in __init__, but that breaks test_bootstrap.py
        k8s_client = k8s_api_client()
        core_api = client.CoreV1Api(k8s_client)
        apps_api = client.AppsV1Api(k8s_client)

        with wrap_context('listing Kubernetes API'):
            deployments = get_fatman_deployments(apps_api)
            pods = get_fatman_pods(core_api)

        for resource_name, deployment in deployments.items():
            pod = pods.get(resource_name)
            if pod is None:
                continue

            metadata: V1ObjectMeta = pod.metadata
            fatman_name = metadata.labels.get(K8S_FATMAN_NAME_LABEL)
            fatman_version = metadata.labels.get(K8S_FATMAN_VERSION_LABEL)
            if not (fatman_name and fatman_version):
                continue

            start_timestamp = datetime_to_timestamp(pod.metadata.creation_timestamp)
            fatman = FatmanDto(
                name=fatman_name,
                version=fatman_version,
                status=FatmanStatus.RUNNING.value,
                create_time=start_timestamp,
                update_time=start_timestamp,
                manifest=None,
                internal_name=fatman_internal_name(resource_name, '', config.deployer),
                error=None,
            )
            try:
                fatman_url = self._get_internal_fatman_url(fatman)
                quick_check_fatman_condition(fatman_url)
                fatman_metrics = scrape_metrics(f'{fatman_url}/metrics')
                fatman.last_call_time = read_last_call_timestamp_metric(fatman_metrics)
            except Exception as e:
                error_details = short_exception_details(e)
                fatman.error = error_details
                fatman.status = FatmanStatus.ERROR.value
                logger.warning(f'Fatman {fatman} is in bad condition: {error_details}')
            yield fatman

    def check_fatman_condition(self,
                               fatman: FatmanDto,
                               deployment_timestamp: int = 0,
                               on_fatman_alive: Callable = None,
                               logs_on_error: bool = True,
                               ):
        try:
            check_until_fatman_is_operational(self._get_internal_fatman_url(fatman),
                                              deployment_timestamp, on_fatman_alive)
        except Exception as e:
            if logs_on_error:
                try:
                    logs = self.read_recent_logs(fatman)
                except (AssertionError, ApiException, CommandError):
                    raise RuntimeError(str(e))
                raise RuntimeError(f'{e}\nFatman logs:\n{logs}')
            else:
                raise RuntimeError(str(e))

    def read_recent_logs(self, fatman: FatmanDto, tail: int = 20) -> str:
        resource_name = fatman_resource_name(fatman.name, fatman.version)
        return shell_output(f'kubectl logs'
                            f' --selector {K8S_FATMAN_RESOURCE_LABEL}={resource_name}'
                            f' -n {K8S_NAMESPACE}'
                            f' --tail={tail}'
                            f' --container={resource_name}')

    def _get_internal_fatman_url(self, fatman: FatmanDto) -> str:
        return f'http://{fatman.internal_name}.{K8S_NAMESPACE}.svc:7000'
