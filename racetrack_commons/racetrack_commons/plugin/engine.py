from typing import Callable, List, Tuple, Optional
from typing import Optional
import time
from racetrack_client.log.errors import EntityNotFound

from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.loader import load_plugins_from_dir
from racetrack_commons.plugin.plugin_manifest import PluginManifest
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class PluginEngine:
    def __init__(self, plugins_dir: Optional[str] = None):
        self.plugin_manifests: List[PluginManifest] = []
        self.plugins: List[Tuple[PluginManifest, PluginCore]] = []
        if plugins_dir:
            self._load_plugins(plugins_dir)
            self._watch_plugins_changes(plugins_dir)

    def _load_plugins(self, plugins_dir: str):
        start_time = time.time()
        with wrap_context('Loading plugins'):
            self.plugins = load_plugins_from_dir(plugins_dir)
            if self.plugins:
                duration = time.time() - start_time
                logger.info(f'{len(self.plugins)} plugins have been loaded from {plugins_dir} in {duration:.2f}s')

    def invoke_plugin_hook(self, function: Callable, *args, **kwargs) -> List:
        """
        Invoke a hook function in all plugins
        :param function: PluginCore function to invoke
        :param args: positional arguments to pass to the function
        :param kwargs: keyword arguments to pass to the function
        :return: list of return values from each plugin
        """
        function_name = function.__name__
        results = []
        for plugin_manifest, plugin in self.plugins:
            if hasattr(plugin, function_name):
                with wrap_context(f'Invoking hook {function_name} from plugin {plugin_manifest.name}'):
                    logger.debug(f'Invoking hook {function_name} from plugin {plugin_manifest.name}')
                    result = getattr(plugin, function_name)(*args, **kwargs)
                    results.append(result)
        return results

    def invoke_one_plugin_hook(self, plugin_name: str, function: Callable, *args, **kwargs):
        """
        Invoke a hook function for one plugin
        :param plugin_name: name of the plugin
        :param function: PluginCore function to invoke
        :param args: positional arguments to pass to the function
        :param kwargs: keyword arguments to pass to the function
        """
        function_name = function.__name__
        plugin_manifest, plugin = self.find_plugin(plugin_name)
        if hasattr(plugin, function_name):
            with wrap_context(f'Invoking hook {function_name} from plugin {plugin_manifest.name}'):
                logger.debug(f'Invoking hook {function_name} from plugin {plugin_manifest.name}')
                return getattr(plugin, function_name)(*args, **kwargs)
        else:
            logger.warning(f'Plugin {plugin_name} does not have hook {function_name}')
            return None

    def find_plugin(self, name: str) -> Tuple[PluginManifest, PluginCore]:
        for plugin_manifest, plugin in self.plugins:
            if plugin_manifest.name == name:
                return plugin_manifest, plugin
        raise EntityNotFound(f'plugin named "{name}" was not found')

    def _watch_plugins_changes(self, plugins_dir: str):
        pass

    def delete_plugin(self, name: str):
        pass

    def upload_plugin(self, filename: str, file_bytes: bytes):
        pass
