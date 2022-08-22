from typing import Optional, List

from pydantic import BaseModel, Extra, validator

from racetrack_commons.plugin.plugin_config import PluginConfig
from racetrack_commons.deploy.type import DeployerType
from racetrack_client.utils.quantity import Quantity


class Config(BaseModel, extra=Extra.forbid, arbitrary_types_allowed=True):
    """Configuration for Lifecycle server instance"""

    # Log level: debug, info, warn, error
    log_level: str = 'info'

    # API endpoints
    http_addr: str = '0.0.0.0'
    http_port: int = 7202

    # Target environment where to deploy Fatmen:
    # - docker - run container on local docker
    # - kubernetes - run Pod & Service in Kubernetes cluster
    # It should be one of DeployerType enum values, although it might be extended with plugins
    deployer: str = DeployerType.DOCKER.value

    # Image builder address
    image_builder_url: str = 'http://localhost:7201'

    # Pub address seen internally, inside of a cluster
    internal_pub_url: str = 'http://pub:7205/pub'

    # Pub address seen externally, outside of a cluster
    external_pub_url: str = 'http://localhost:7205/pub'

    # Docker Registry storing built images
    docker_registry: str = 'localhost:5000'

    # A namespace for docker images in a Docker Registry (prefix for image names)
    docker_registry_namespace: str = 'racetrack'

    # Are endpoints enforcing authentication
    auth_required: bool = True

    # Adds meaningful details to auth errors
    auth_debug: bool = False

    # List of plugins to load that change behavior of Lifecycle
    plugins: Optional[List[PluginConfig]] = None

    # Max allowed memory of a Fatman that can ever be requested in a cluster.
    # Hard limit of "memory_max" value demanded by Fatman in bytes
    max_fatman_memory_limit: Quantity = Quantity('8Gi')

    # default ranges of resources to allocate to Fatmen
    default_fatman_memory_min: Quantity = Quantity('150Mi')
    default_fatman_memory_max: Quantity = Quantity('600MiB')
    default_fatman_cpu_min: Quantity = Quantity('10m')
    default_fatman_cpu_max: Quantity = Quantity('1000m')

    @validator(
        'max_fatman_memory_limit',
        'default_fatman_memory_min',
        'default_fatman_memory_max',
        'default_fatman_cpu_min',
        'default_fatman_cpu_max',
        pre=True)
    def _validate_quantity(cls, v):
        if v is None:
            return None
        return Quantity(str(v))
