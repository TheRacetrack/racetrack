from __future__ import annotations

from pydantic import BaseModel

from lifecycle.config import Config
from lifecycle.deployer.base import JobDeployer
from lifecycle.monitor.base import JobMonitor, LogsStreamer
from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_client.manifest.manifest import Manifest


class InfrastructureTarget(BaseModel, arbitrary_types_allowed=True):
    job_deployer: JobDeployer
    job_monitor: JobMonitor
    logs_streamer: LogsStreamer


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

    if config.infrastructure_target:
        assert config.infrastructure_target in available_targets, \
            f'Selected infrastructure target "{config.infrastructure_target}" is unavailable. Available are {", ".join(available_targets)}.'
        return config.infrastructure_target
    
    if len(available_targets) == 1:
        return available_targets[0]
    
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


def get_infrastructure_target(
    plugin_engine: PluginEngine, 
    infrastructure_name: str | None,
) -> InfrastructureTarget:
    infrastructures = _gather_infrastructure_targets(plugin_engine)

    if infrastructure_name:
        assert infrastructure_name in infrastructures, f'Selected infrastructure target "{infrastructure_name}" is unavailable'
        return infrastructures[infrastructure_name]

    if len(infrastructures) == 1:
        return next(iter(infrastructures.values()))

    raise RuntimeError('Infrastructure Target is not specified')


def list_infrastructure_names_with_origins(plugin_engine: PluginEngine) -> dict[str, PluginManifest]:
    infra_names_with_origins: dict[str, PluginManifest] = {}
    for plugin_manifest, result in plugin_engine.invoke_associated_plugin_hook(PluginCore.infrastructure_targets).items():
        if result:
            for infra_name in result.keys():
                infra_names_with_origins[infra_name] = plugin_manifest
    return infra_names_with_origins
