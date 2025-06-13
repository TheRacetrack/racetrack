from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

from racetrack_client.utils.quantity import Quantity


class Config(BaseModel):
    """Configuration for Lifecycle server instance"""
    model_config = ConfigDict(extra='forbid', arbitrary_types_allowed=True)

    # Log level: debug, info, warn, error
    log_level: str = 'info'

    # API endpoints
    http_addr: str = '0.0.0.0'
    http_port: int = 7202

    # Image builder address
    image_builder_url: str = 'http://127.0.0.1:7201'

    # Pub address seen internally, inside of a cluster
    internal_pub_url: str = 'http://pub:7205/pub'

    # Pub address seen externally, outside of a cluster
    external_pub_url: str = 'http://127.0.0.1:7205/pub'

    # Docker Registry storing built images
    docker_registry: str = '127.0.0.1:5000'

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

    # How often (in seconds) to check for changes made to jobs in a database and notify live clients
    job_watcher_interval: float = 3

    # How often (in seconds) to check if there is vital connection to database. 0 value disables this check.
    database_status_refresh_interval: float = 60
    # Maximum number of connections in the datbase connection pool
    database_connection_pool: int = 20
    # Whether to print logs about every executed SQL query
    database_log_queries: bool = False

    # Whether to allow overwriting existing jobs by deploying the same version once again
    allow_job_overwrite: bool = False

    # Retention in seconds of Async job call models
    async_job_call_lifetime: int = 4 * 3600

    # Maximum number of seconds to wait until the job is alive in the cluster (/live endpoint responds)
    timeout_until_job_alive: int = 15 * 60
    # Maximum number of seconds to wait until the job is ready (initialized)
    timeout_until_job_ready: int = 10 * 60

    # Number of threads in thread pool of HTTP worker - maximum number of concurrent requests
    # By default, there are 40 threads available in the thread pool in FastAPI/anyio.
    http_worker_thread_pool: Optional[int] = 60

    # Whether reconciliation loop is enabled or not.
    # Reconciliation loop is an automated, periodic process that restores missing jobs by re-provisioning them
    reconciliation_loop: bool = False

    @field_validator(
        'max_job_memory_limit',
        'default_job_memory_min',
        'default_job_memory_max',
        'default_job_cpu_min',
        'default_job_cpu_max',
        mode='before')
    @classmethod
    def _quantity_field_must_be_valid(cls, v: str) -> Optional[Quantity]:
        if v is None:
            return None
        return Quantity(str(v))
