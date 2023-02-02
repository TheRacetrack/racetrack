from typing import Dict, List

from racetrack_client.utils.datamodel import parse_dict_datamodels
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.entities.dto import JobDto, JobFamilyDto
from racetrack_commons.entities.lifecycle_client import LifecycleClient


class JobRegistryClient:
    def __init__(self, auth_token: str = ''):
        self.lc_client = LifecycleClient(auth_token)

    def list_deployed_jobs(self) -> List[JobDto]:
        response = self.lc_client.request_list('get', '/api/v1/job')
        return parse_dict_datamodels(response, JobDto)

    def list_deployed_job_families(self) -> List[JobFamilyDto]:
        response = self.lc_client.request_list('get', '/api/v1/job_family')
        return parse_dict_datamodels(response, JobFamilyDto)

    def delete_deployed_job(self, job.name: str, job.version: str):
        self.lc_client.request('delete', f'/api/v1/job/{job.name}/{job.version}')

    def redeploy_job(self, job.name: str, job.version: str):
        self.lc_client.request('post', f'/api/v1/job/{job.name}/{job.version}/redeploy')

    def reprovision_job(self, job.name: str, job.version: str):
        self.lc_client.request('post', f'/api/v1/job/{job.name}/{job.version}/reprovision')

    def get_dependencies_graph(self) -> Dict:
        return self.lc_client.request_dict('get', '/api/v1/job_graph')

    def job_allow_job(self, source_family_name: str, target_family_name: str):
        """
        It will make target job be callable from source job.
        """
        scope = AuthScope.CALL_JOB.value
        self.lc_client.request('post', f'/api/v1/auth/allow/job_family/{source_family_name}/job/{target_family_name}/scope/{scope}')

    def get_runtime_logs(self, job.name: str, job.version: str, tail: int = 0) -> str:
        params = {}
        if tail > 0:
            params['tail'] = tail
        response = self.lc_client.request_dict('get', f'/api/v1/job/{job.name}/{job.version}/logs', params=params)
        return response['logs']

    def get_build_logs(self, job.name: str, job.version: str, tail: int = 0) -> str:
        params = {}
        if tail > 0:
            params['tail'] = tail
        response = self.lc_client.request_dict('get', f'/api/v1/job/{job.name}/{job.version}/build-logs', params=params)
        return response['logs']
