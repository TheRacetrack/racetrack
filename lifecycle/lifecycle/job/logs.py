from lifecycle.config import Config
from lifecycle.django.registry import models
from lifecycle.fatman.registry import read_versioned_fatman
from lifecycle.fatman import models_registry
from lifecycle.monitor.monitors import read_recent_logs
from racetrack_client.log.errors import EntityNotFound
from racetrack_commons.plugin.engine import PluginEngine


def read_runtime_logs(fatman_name: str, fatman_version: str, tail: int, config: Config, plugin_engine: PluginEngine) -> str:
    """Read recent logs from running fatman by its name"""
    fatman = read_versioned_fatman(fatman_name, fatman_version, config)
    return read_recent_logs(fatman, tail, plugin_engine)


def read_build_logs(fatman_name: str, fatman_version: str, tail: int) -> str:
    """Read build logs from fatman image during latest fatman deployment"""
    fatman_model = models_registry.resolve_fatman_model(fatman_name, fatman_version)
    deployments_queryset = models.Deployment.objects\
        .filter(fatman_name=fatman_model.name, fatman_version=fatman_model.version)\
        .order_by('-update_time')
    if deployments_queryset.count() == 0:
        raise EntityNotFound(f'No deployment matching to a fatman {fatman_name}')
    latest_deployment: models.Deployment = list(deployments_queryset)[0]
    logs: str = latest_deployment.build_logs or ''
    if tail > 0:
        logs = '\n'.join(logs.splitlines()[-tail:])
    return logs
