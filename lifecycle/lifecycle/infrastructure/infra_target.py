from lifecycle.config import Config
from lifecycle.infrastructure.model import InfrastructureTarget
from lifecycle.server.cache import LifecycleCache
from racetrack_client.manifest.manifest import Manifest
from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_client.utils.request import Requests, parse_response_object
from racetrack_client.utils.shell import CommandError
from racetrack_client.utils.url import join_paths
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine


def determine_infrastructure_name(
    config: Config,
    plugin_engine: PluginEngine,
    manifest: Manifest,
) -> str:
    available_targets = list_infrastructure_names(plugin_engine)
    assert available_targets, 'No infrastructure targets available. Install appropriate plugin.'

    if manifest.infrastructure_target:
        assert manifest.infrastructure_target in available_targets, \
            f'Selected infrastructure target "{manifest.infrastructure_target}" is unavailable. Available are {", ".join(available_targets)}.'
        return manifest.infrastructure_target

    if len(available_targets) == 1:
        return available_targets[0]

    if config.infrastructure_target:
        assert config.infrastructure_target in available_targets, \
            f'Selected infrastructure target "{config.infrastructure_target}" is unavailable. Available are {", ".join(available_targets)}.'
        return config.infrastructure_target

    raise RuntimeError(f'Multiple infrastructure targets available: {available_targets}. Please pick one.')


def list_infrastructure_names(plugin_engine: PluginEngine) -> list[str]:
    infrastructures = _gather_infrastructure_targets(plugin_engine)
    return sorted(infrastructures.keys())


def list_infrastructure_targets(plugin_engine: PluginEngine) -> list[InfrastructureTarget]:
    infrastructures = _gather_infrastructure_targets(plugin_engine)
    return list(infrastructures.values())


def _gather_infrastructure_targets(plugin_engine: PluginEngine) -> dict[str, InfrastructureTarget]:
    all_infrastructures: dict[str, InfrastructureTarget] = {}
    for result in plugin_engine.invoke_plugin_hook(PluginCore.infrastructure_targets):
        if result:
            all_infrastructures.update(result)
    return all_infrastructures


def get_infrastructure_target(infrastructure_name: str | None) -> InfrastructureTarget:
    infrastructures: dict[str, InfrastructureTarget] = LifecycleCache.infrastructure_targets

    if infrastructure_name:
        assert infrastructure_name in infrastructures, f'Selected infrastructure target "{infrastructure_name}" is unavailable'
        return infrastructures[infrastructure_name]

    if len(infrastructures) == 1:
        return next(iter(infrastructures.values()))

    raise RuntimeError('Infrastructure Target is not specified')


def list_infrastructure_names_with_origins(plugin_engine: PluginEngine) -> dict[str, PluginManifest]:
    infra_names_with_origins: dict[str, PluginManifest] = {}
    for plugin_data, result in plugin_engine.invoke_hook_with_origin(PluginCore.infrastructure_targets):
        if result:
            for infra_name in result.keys():
                infra_names_with_origins[infra_name] = plugin_data.plugin_manifest
    return infra_names_with_origins


def list_infrastructure_names_of_plugins(plugin_engine: PluginEngine) -> list[tuple[PluginManifest, str]]:
    entries: list[tuple[PluginManifest, str]] = []
    for plugin_data, result in plugin_engine.invoke_hook_with_origin(PluginCore.infrastructure_targets):
        if result:
            for infra_name in result.keys():
                entries.append((plugin_data.plugin_manifest, infra_name))
    return entries


class RemoteCommandError(CommandError):
    def __init__(self, cmd: str, stdout: str, returncode: int):
        super().__init__(cmd, stdout, returncode)

    def __str__(self):
        return f'remote command failed: {self.cmd}: {self.stdout}'


def remote_shell(
    cmd: str,
    remote_gateway_url: str,
    remote_gateway_token: str | None = None,
    workdir: str | None = None,
) -> str:
    """
    Run command on remote infrastructure, return output of a command.
    Output is combined standard output and standard error.
    """
    url = join_paths(remote_gateway_url, "/remote/command")
    response = Requests.post(url, headers={
        'X-Racetrack-Gateway-Token': remote_gateway_token,
    }, json={
        'command': cmd,
        'workdir': workdir,
    })
    response_data = parse_response_object(response, 'Pub response')
    output = response_data['output']
    exit_code = int(response_data['exit_code'])
    if exit_code != 0:
        raise RemoteCommandError(cmd, output, exit_code)
    return output
