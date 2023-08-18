from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.deployer.infra_target import InfrastructureTarget


class LifecycleCache:
    infrastructure_targets: dict[str, InfrastructureTarget] = {}

    @classmethod
    def on_plugins_reload(cls, plugin_engine: PluginEngine):
        cls.infrastructure_targets = {}
        for result in plugin_engine.invoke_plugin_hook(PluginCore.infrastructure_targets):
            if result:
                cls.infrastructure_targets.update(result)
