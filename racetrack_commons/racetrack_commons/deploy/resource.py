from racetrack_client.manifest import Manifest
from racetrack_commons.deploy.job_type import load_job_type
from racetrack_commons.plugin.engine import PluginEngine


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


def count_job_type_containers(
    manifest: Manifest,
    plugin_engine: PluginEngine,
) -> int:
    """Determine number of containers used by a job type"""
    job_type = load_job_type(plugin_engine, manifest.lang)
    return len(job_type.template_paths)
