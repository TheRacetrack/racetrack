from __future__ import annotations

from lifecycle.deployer.base import JobDeployer
from lifecycle.deployer.infra_target import get_infrastructure_target
from racetrack_commons.plugin.engine import PluginEngine


def get_job_deployer(
    plugin_engine: PluginEngine,
    infrastructure_name: str | None,
) -> JobDeployer:
    infra_target = get_infrastructure_target(plugin_engine, infrastructure_name)
    return infra_target.job_deployer
