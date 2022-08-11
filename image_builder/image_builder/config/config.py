from typing import Optional, List

from pydantic import BaseModel, Extra

from racetrack_commons.plugin.plugin_config import PluginConfig


class Config(BaseModel, extra=Extra.forbid):
    """Configuration for Image Builder instance"""

    # Log level: debug, info, warn, error
    log_level: str = 'info'

    # API endpoints
    http_addr: str = '0.0.0.0'
    http_port: int = 7201

    # Docker Registry where to push built images
    docker_registry: str = 'localhost:5000'

    # A namespace for docker images in a Docker Registry (prefix for image names)
    docker_registry_namespace: str = 'racetrack'

    # Directory name where to store build logs for each image
    build_logs_dir: str = './.build-logs'

    # Retention period after which build cache objects are deleted
    # None - pruning cache is disabled
    build_cache_retention_hours: Optional[float] = None

    # Interval (in minutes) between tasks pruning build cache
    build_cache_prune_interval_m: float = 60

    # List of plugins to load that change behavior of Lifecycle
    plugins: Optional[List[PluginConfig]] = None

    # Remove workspace directories after building
    clean_up_workspaces: bool = True
