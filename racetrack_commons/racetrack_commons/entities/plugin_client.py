from typing import List, Optional

from racetrack_client.utils.datamodel import parse_dict_datamodels
from racetrack_client.utils.request import Requests, parse_response
from racetrack_commons.entities.lifecycle_client import LifecycleClient
from racetrack_commons.plugin.plugin_manifest import PluginManifest


class LifecyclePluginClient:
    def __init__(self, auth_token: str = ''):
        self.lc_client = LifecycleClient(auth_token)

    def get_plugins_info(self) -> List[PluginManifest]:
        response = self.lc_client.request_list('get', '/api/v1/plugins')
        return parse_dict_datamodels(response, PluginManifest)

    def get_plugin_docs(self, plugin_name: str) -> Optional[str]:
        return self.lc_client.request_dict('get', f'/api/v1/plugin/{plugin_name}/docs')

    def delete_plugin(self, plugin_name: str, plugin_version: str):
        self.lc_client.request('delete', f'/api/v1/plugin/{plugin_name}/{plugin_version}')

    def upload_plugin(self, filename: str, file_bytes: bytes):
        r = Requests.post(f'{self.lc_client._lifecycle_api_url}/api/v1/plugin/upload/{filename}',
                          data=file_bytes,
                          headers=self.lc_client._get_auth_headers())
        parse_response(r, 'Lifecycle response')
