from __future__ import annotations

from lifecycle.config import Config
from lifecycle.deployer.base import FatmanDeployer
from lifecycle.deployer.docker.docker import DockerFatmanDeployer
from lifecycle.deployer.kubernetes.kubernetes import KubernetesFatmanDeployer
from racetrack_commons.deploy.type import DeployerType
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine


"""Supported fatman deployers for different platforms"""
std_fatman_deployers: dict[str, FatmanDeployer] = {
    DeployerType.DOCKER.value: DockerFatmanDeployer(),
    DeployerType.KUBERNETES.value: KubernetesFatmanDeployer(),
}


def get_fatman_deployer(config: Config, plugin_engine: PluginEngine) -> FatmanDeployer:
    plugin_deployers = _gather_plugin_fatman_deployers(plugin_engine)
    if len(plugin_deployers) == 1:
        return next(iter(plugin_deployers.values()))

    all_fatman_deployers = {**std_fatman_deployers, **plugin_deployers}
    assert config.deployer in all_fatman_deployers, f'not supported fatman deployer: {config.deployer}'
    return all_fatman_deployers[config.deployer]


def _gather_plugin_fatman_deployers(
    plugin_engine: PluginEngine,
) -> dict[str, FatmanDeployer]:
    plugin_fatman_deployers = {}

    plugin_results = plugin_engine.invoke_plugin_hook(PluginCore.fatman_deployers)
    for plugin_deployers in plugin_results:
        for deployer_name, deployer in plugin_deployers.items():
            plugin_fatman_deployers[deployer_name] = deployer

    return plugin_fatman_deployers
