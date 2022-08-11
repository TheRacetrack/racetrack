import os
from typing import List, Dict

from kubernetes import client
from kubernetes.client import V1ObjectMeta, V1Pod, V1Deployment
from kubernetes.config import load_incluster_config

K8S_NAMESPACE = os.environ.get('FATMAN_K8S_NAMESPACE', 'racetrack')
K8S_FATMAN_RESOURCE_LABEL = "racetrack/fatman"
K8S_FATMAN_NAME_LABEL = "racetrack/fatman-name"
K8S_FATMAN_VERSION_LABEL = "racetrack/fatman-version"


def k8s_api_client() -> client.ApiClient:
    load_incluster_config()
    return client.ApiClient()


def get_recent_fatman_pod(pods: List[V1Pod]) -> str:
    """If many pods are found, return the latest alive pod"""
    assert pods, 'no pod found with expected fatman label'
    pods_alive = [pod for pod in pods if pod.metadata.deletion_timestamp is None]  # ignore Terminating pods
    assert pods_alive, 'no alive pod found with expected fatman label'
    recent_pod = sorted(pods_alive, key=lambda pod: pod.metadata.creation_timestamp)[-1]
    metadata: V1ObjectMeta = recent_pod.metadata
    return metadata.name


def get_fatman_pod_names(pods: List[V1Pod]) -> List[str]:
    """Get alive fatman pods names"""
    assert pods, 'empty pods list'
    pods_alive = [pod for pod in pods if pod.metadata.deletion_timestamp is None]  # ignore Terminating pods
    assert pods_alive, 'no alive pod found'
    return [pod.metadata.name for pod in pods_alive]


def get_fatman_deployments(apps_api: client.AppsV1Api) -> Dict[str, V1Deployment]:
    fat_deployments = {}
    _continue = None  # pointer to the query in case of multiple pages
    while True:
        ret = apps_api.list_namespaced_deployment(K8S_NAMESPACE, limit=100, _continue=_continue)
        deployments: List[V1Deployment] = ret.items

        for deployment in deployments:
            metadata: V1ObjectMeta = deployment.metadata
            if K8S_FATMAN_RESOURCE_LABEL in metadata.labels:
                name = metadata.labels[K8S_FATMAN_RESOURCE_LABEL]
                fat_deployments[name] = deployment

        _continue = ret.metadata._continue
        if _continue is None:
            break

    return fat_deployments


def get_fatman_pods(core_api: client.CoreV1Api) -> Dict[str, V1Pod]:
    fat_pods = {}
    _continue = None  # pointer to the query in case of multiple pages
    while True:
        ret = core_api.list_namespaced_pod(K8S_NAMESPACE, limit=100, _continue=_continue)
        pods: List[V1Pod] = ret.items

        for pod in pods:
            metadata: V1ObjectMeta = pod.metadata
            # omit terminating pods by checking deletion_timestamp,
            # because that's only way to get solid info whether pod has been deleted;
            # pod statuses can have few seconds of delay
            if pod.metadata.deletion_timestamp is not None:
                continue

            if K8S_FATMAN_RESOURCE_LABEL in metadata.labels:
                name = metadata.labels[K8S_FATMAN_RESOURCE_LABEL]
                fat_pods[name] = pod

        _continue = ret.metadata._continue
        if _continue is None:
            break

    return fat_pods
