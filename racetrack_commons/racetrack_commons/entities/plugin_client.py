from __future__ import annotations

from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_client.utils.datamodel import parse_dict_datamodels
from racetrack_client.utils.request import Requests, parse_response
from racetrack_commons.entities.lifecycle_client import LifecycleClient


class LifecyclePluginClient:
    def __init__(self, auth_token: str = ''):
        self.lc_client = LifecycleClient(auth_token)

    def get_plugins_info(self) -> list[PluginManifest]:
        response = self.lc_client.request_list('get', '/api/v1/plugin')
        return parse_dict_datamodels(response, PluginManifest)

    def get_job_type_versions(self) -> list[str]:
        return self.lc_client.request_list('get', '/api/v1/plugin/job_type/versions')
        
    def get_infrastructure_targets(self) -> dict[str, PluginManifest]:
        return self.lc_client.request_dict('get', '/api/v1/plugin/infrastructure_targets')

    def get_plugin_docs(self, plugin_name: str) -> str | None:
        return self.lc_client.request('get', f'/api/v1/plugin/{plugin_name}/docs')

    def delete_plugin(self, plugin_name: str, plugin_version: str):
        self.lc_client.request('delete', f'/api/v1/plugin/{plugin_name}/{plugin_version}')

    def upload_plugin(self, filename: str, file_bytes: bytes):
        r = Requests.post(f'{self.lc_client._lifecycle_api_url}/api/v1/plugin/upload/{filename}',
                          data=file_bytes,
                          headers=self.lc_client._get_auth_headers())
        parse_response(r, 'Lifecycle response')

    def read_plugin_config(self, plugin_name: str, plugin_version: str) -> str:
        return self.lc_client.request('get', f'/api/v1/plugin/{plugin_name}/{plugin_version}/config')

    def write_plugin_config(self, plugin_name: str, plugin_version: str, config_data: str) -> str:
        return self.lc_client.request('put', f'/api/v1/plugin/{plugin_name}/{plugin_version}/config',
            json={'config_data': config_data},
        )
