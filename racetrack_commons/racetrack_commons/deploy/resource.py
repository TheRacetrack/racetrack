from racetrack_commons.api.debug import is_deployment_local
from racetrack_commons.deploy.type import DeployerType

FATMAN_INTERNAL_PORT = 7000  # Fatman listening port seen from inside the container


def fatman_resource_name(fatman_name: str, fatman_version: str) -> str:
    """
    Assemble internal resource name inside a cluster for a particular Fatman.
    The name of a Service object must be a valid RFC 1035 label name.
    """
    return f'fatman-{fatman_name}-v-{fatman_version}'.replace('.', '-')


def fatman_user_module_resource_name(fatman_name: str, fatman_version: str) -> str:
    """Assemble resource name of Fatman's user module (user-defined container for Dockerfile job type)"""
    base_resource_name = fatman_resource_name(fatman_name, fatman_version)
    return f'{base_resource_name}-user-module'


def fatman_internal_name(resource_name: str, fatman_port: str, deployer: str):
    if deployer == DeployerType.DOCKER.value:
        if is_deployment_local():
            return f'localhost:{fatman_port}'
        else:
            return f'{resource_name}:{FATMAN_INTERNAL_PORT}'
    else:  # k8s
        return resource_name
