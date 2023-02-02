from typing import Dict, List

from racetrack_client.utils.datamodel import parse_dict_datamodels
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.entities.dto import FatmanDto, FatmanFamilyDto
from racetrack_commons.entities.lifecycle_client import LifecycleClient


class FatmanRegistryClient:
    def __init__(self, auth_token: str = ''):
        self.lc_client = LifecycleClient(auth_token)

    def list_deployed_fatmen(self) -> List[FatmanDto]:
        response = self.lc_client.request_list('get', '/api/v1/fatman')
        return parse_dict_datamodels(response, FatmanDto)

    def list_deployed_fatman_families(self) -> List[FatmanFamilyDto]:
        response = self.lc_client.request_list('get', '/api/v1/fatman_family')
        return parse_dict_datamodels(response, FatmanFamilyDto)

    def delete_deployed_fatman(self, fatman_name: str, fatman_version: str):
        self.lc_client.request('delete', f'/api/v1/fatman/{fatman_name}/{fatman_version}')

    def redeploy_fatman(self, fatman_name: str, fatman_version: str):
        self.lc_client.request('post', f'/api/v1/fatman/{fatman_name}/{fatman_version}/redeploy')

    def reprovision_fatman(self, fatman_name: str, fatman_version: str):
        self.lc_client.request('post', f'/api/v1/fatman/{fatman_name}/{fatman_version}/reprovision')

    def get_dependencies_graph(self) -> Dict:
        return self.lc_client.request_dict('get', '/api/v1/fatman_graph')

    def fatman_allow_fatman(self, source_family_name: str, target_family_name: str):
        """
        It will make target fatman be callable from source fatman.
        """
        scope = AuthScope.CALL_FATMAN.value
        self.lc_client.request('post', f'/api/v1/auth/allow/fatman_family/{source_family_name}/fatman/{target_family_name}/scope/{scope}')

    def get_runtime_logs(self, fatman_name: str, fatman_version: str, tail: int = 0) -> str:
        params = {}
        if tail > 0:
            params['tail'] = tail
        response = self.lc_client.request_dict('get', f'/api/v1/fatman/{fatman_name}/{fatman_version}/logs', params=params)
        return response['logs']

    def get_build_logs(self, fatman_name: str, fatman_version: str, tail: int = 0) -> str:
        params = {}
        if tail > 0:
            params['tail'] = tail
        response = self.lc_client.request_dict('get', f'/api/v1/fatman/{fatman_name}/{fatman_version}/build-logs', params=params)
        return response['logs']
