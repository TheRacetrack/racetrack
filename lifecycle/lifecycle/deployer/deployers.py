from typing import Dict

from lifecycle.config import Config
from lifecycle.deployer.base import FatmanDeployer
from lifecycle.deployer.docker.docker import DockerFatmanDeployer
from lifecycle.deployer.kubernetes.kubernetes import KubernetesFatmanDeployer
from racetrack_commons.deploy.type import DeployerType
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine


"""Supported fatman deployers for different platforms"""
std_fatman_deployers: Dict[str, FatmanDeployer] = {
    DeployerType.DOCKER.value: DockerFatmanDeployer(),
    DeployerType.KUBERNETES.value: KubernetesFatmanDeployer(),
}


def get_fatman_deployer(config: Config, plugin_engine: PluginEngine) -> FatmanDeployer:
    all_fatman_deployers = _gather_fatman_deployers(plugin_engine)
    assert config.deployer in all_fatman_deployers, f'not supported fatman deployer: {config.deployer}'
    return all_fatman_deployers[config.deployer]


def _gather_fatman_deployers(
    plugin_engine: PluginEngine,
) -> Dict[str, FatmanDeployer]:
    all_fatman_deployers = std_fatman_deployers

    plugin_results = plugin_engine.invoke_plugin_hook(PluginCore.fatman_deployers)
    for plugin_deployers in plugin_results:
        for deployer_name, deployer in plugin_deployers.items():
            all_fatman_deployers[deployer_name] = deployer

    return all_fatman_deployers
