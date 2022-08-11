from typing import Callable, List, Tuple, Optional
from typing import Optional
import time
from racetrack_client.log.errors import EntityNotFound

from racetrack_commons.plugin.plugin_config import PluginConfig
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.loader import load_plugin
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger


logger = get_logger(__name__)


class PluginEngine:
    def __init__(self, plugin_configs: Optional[List[PluginConfig]] = None):
        self.plugin_configs: List[PluginConfig] = plugin_configs or []
        self.plugins: List[Tuple[PluginConfig, PluginCore]] = []
        self._load_plugins()

    def _load_plugins(self):
        start_time = time.time()
        plugins = [(plugin_config, load_plugin(plugin_config)) 
                   for plugin_config in self.plugin_configs]
        self.plugins = sorted(plugins, key=lambda plugin: plugin[0].priority)
        duration = time.time() - start_time
        if plugins:
            logger.debug(f'{len(plugins)} plugins have been loaded in {duration:.2f}s')

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
        for plugin_config, plugin in self.plugins:
            if hasattr(plugin, function_name):
                with wrap_context(f'Invoking hook {function_name} from plugin {plugin_config.name}'):
                    logger.debug(f'Invoking hook {function_name} from plugin {plugin_config.name}')
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
        :return: list of return values from each plugin
        """
        function_name = function.__name__
        plugin_config, plugin = self.find_plugin(plugin_name)
        if hasattr(plugin, function_name):
            with wrap_context(f'Invoking hook {function_name} from plugin {plugin_config.name}'):
                logger.debug(f'Invoking hook {function_name} from plugin {plugin_config.name}')
                return getattr(plugin, function_name)(*args, **kwargs)
        else:
            logger.warning(f'Plugin {plugin_name} does not have hook {function_name}')
            return None

    def find_plugin(self, name: str) -> Tuple[PluginConfig, PluginCore]:
        for plugin_config, plugin in self.plugins:
            if plugin_config.name == name:
                return plugin_config, plugin
        raise EntityNotFound(f'plugin named "{name}" was not found')
