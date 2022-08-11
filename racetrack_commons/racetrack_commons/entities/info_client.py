from typing import List

from racetrack_client.utils.datamodel import parse_dict_datamodels
from racetrack_commons.entities.dto import PluginConfigDto
from racetrack_commons.entities.lifecycle_client import LifecycleClient


class LifecycleInfoClient:
    def __init__(self):
        self.lc_client = LifecycleClient()

    def get_plugins_info(self) -> List[PluginConfigDto]:
        response = self.lc_client.request_list('get', f'/api/v1/info/plugins')
        return parse_dict_datamodels(response, PluginConfigDto)

    def get_plugin_docs(self, plugin_name: str) -> str:
        return self.lc_client.request_dict('get', f'/api/v1/info/plugin/{plugin_name}/docs')
