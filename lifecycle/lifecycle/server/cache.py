from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.deployer.infra_target import InfrastructureTarget
from lifecycle.monitor.monitors import list_log_streamers
from lifecycle.server.socketio import SocketIOServer


class LifecycleCache:
    infrastructure_targets: dict[str, InfrastructureTarget] = {}
    socketio_server: SocketIOServer | None = None

    @classmethod
    def on_plugins_reload(cls, plugin_engine: PluginEngine):
        cls.infrastructure_targets = {}
        for result in plugin_engine.invoke_plugin_hook(PluginCore.infrastructure_targets):
            if result:
                cls.infrastructure_targets.update(result)

        if cls.socketio_server is not None:
            cls.socketio_server.log_streamers = list_log_streamers(plugin_engine)
