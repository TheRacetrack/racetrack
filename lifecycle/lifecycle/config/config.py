from typing import Optional
from pydantic import BaseModel, Extra, validator

from racetrack_client.utils.quantity import Quantity


class Config(BaseModel, extra=Extra.forbid, arbitrary_types_allowed=True):
    """Configuration for Lifecycle server instance"""

    # Log level: debug, info, warn, error
    log_level: str = 'info'

    # API endpoints
    http_addr: str = '0.0.0.0'
    http_port: int = 7202

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

    # Path to a directory with plugins to be loaded from
    plugins_dir: str = '.plugins'

    # Max allowed memory of a Job that can ever be requested in a cluster.
    # Hard limit of "memory_max" value demanded by Job in bytes
    max_job_memory_limit: Quantity = Quantity('8Gi')

    # default ranges of resources to allocate to Jobs
    default_job_memory_min: Quantity = Quantity('256Mi')
    default_job_memory_max: Quantity = Quantity('1Gi')
    default_job_cpu_min: Quantity = Quantity('10m')
    default_job_cpu_max: Quantity = Quantity('1000m')

    # OpenTelemetry
    open_telemetry_enabled: bool = False
    open_telemetry_endpoint: str = 'console'

    # Default back-end platform where to deploy the services
    infrastructure_target: Optional[str] = None

    @validator(
        'max_job_memory_limit',
        'default_job_memory_min',
        'default_job_memory_max',
        'default_job_cpu_min',
        'default_job_cpu_max',
        pre=True)
    def _validate_quantity(cls, v):
        if v is None:
            return None
        return Quantity(str(v))
