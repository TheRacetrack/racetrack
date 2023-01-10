from __future__ import annotations

from lifecycle.deployer.base import FatmanDeployer
from lifecycle.deployer.infra_target import get_infrastructure_target
from racetrack_commons.plugin.engine import PluginEngine


def get_fatman_deployer(
    plugin_engine: PluginEngine,
    infrastructure_name: str | None,
) -> FatmanDeployer:
    infra_target = get_infrastructure_target(plugin_engine, infrastructure_name)
    return infra_target.fatman_deployer
