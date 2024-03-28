from racetrack_client.log.context_error import wrap_context
from racetrack_commons.deploy.job_type import JobType, gather_job_types
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.infrastructure.model import InfrastructureTarget


class LifecycleCache:
    infrastructure_targets: dict[str, InfrastructureTarget] = {}
    job_types: dict[str, JobType] = {}

    @classmethod
    def on_plugins_reload(cls, plugin_engine: PluginEngine):
        with wrap_context('gathering infrastructure targets'):
            cls.infrastructure_targets = {}
            for result in plugin_engine.invoke_plugin_hook(PluginCore.infrastructure_targets):
                if result:
                    cls.infrastructure_targets.update(result)

        with wrap_context('gathering available job types'):
            cls.job_types = gather_job_types(plugin_engine)
