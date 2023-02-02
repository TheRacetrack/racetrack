from typing import List, Optional

from racetrack_client.utils.datamodel import parse_dict_datamodels
from racetrack_commons.entities.dto import AuditLogEventDto
from racetrack_commons.entities.lifecycle_client import LifecycleClient


class AuditClient:
    def __init__(self, auth_token: str = ''):
        self.lc_client = LifecycleClient(auth_token)

    def list_user_events(self) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', '/api/v1/audit/user_events')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def list_user_job_family_events(self, job_name: str) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', f'/api/v1/audit/user_events/job/{job_name}')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def list_user_job_events(self, job_name: str, job_version: str) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', f'/api/v1/audit/user_events/job/{job_name}/{job_version}')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def list_all_events(self) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', '/api/v1/audit/events')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def list_job_family_events(self, job_name: str) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', f'/api/v1/audit/events/job/{job_name}')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def list_job_events(self, job_name: str, job_version: str) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', f'/api/v1/audit/events/job/{job_name}/{job_version}')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def filter_events(self, 
        related_to_user: bool, 
        job_name: Optional[str], 
        job_version: Optional[str],
    ) -> List[AuditLogEventDto]:
        if related_to_user:
            if job_name and job_version:
                return self.list_user_job_events(job_name, job_version)
            elif job_name:
                return self.list_user_job_family_events(job_name)
            else:
                return self.list_user_events()
        else:
            if job_name and job_version:
                return self.list_job_events(job_name, job_version)
            elif job_name:
                return self.list_job_family_events(job_name)
            else:
                return self.list_all_events()
