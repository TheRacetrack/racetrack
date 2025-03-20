from typing import List, Optional

from racetrack_client.utils.datamodel import parse_dict_datamodel, parse_dict_datamodels
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.entities.dto import EscDto
from racetrack_commons.entities.lifecycle_client import LifecycleClient


class EscRegistryClient:
    def __init__(self, auth_token: str = ''):
        self.lc_client = LifecycleClient(auth_token)

    def create_esc(self, name: str, esc_id: Optional[str] = None) -> EscDto:
        response = self.lc_client.request_dict('post', '/api/v1/escs', json={'name': name, 'id': esc_id})
        return parse_dict_datamodel(response, EscDto)

    def esc_allow_job(self, esc_id: str, job_name: str):
        scope = AuthScope.CALL_JOB.value
        self.lc_client.request('post', f'/api/v1/auth/allow/esc/{esc_id}/job/{job_name}/scope/{scope}')

    def get_esc_auth_token(self, esc_id: str) -> str:
        response = self.lc_client.request_dict('get', f'/api/v1/auth/token/esc/{esc_id}')
        return response['token']

    def list_escs(self) -> List[EscDto]:
        response = self.lc_client.request_list('get', '/api/v1/escs')
        return parse_dict_datamodels(response, EscDto)
