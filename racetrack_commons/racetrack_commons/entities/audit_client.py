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

    def list_user_fatman_family_events(self, fatman_name: str) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', f'/api/v1/audit/user_events/fatman/{fatman_name}')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def list_user_fatman_events(self, fatman_name: str, fatman_version: str) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', f'/api/v1/audit/user_events/fatman/{fatman_name}/{fatman_version}')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def list_all_events(self) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', '/api/v1/audit/events')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def list_fatman_family_events(self, fatman_name: str) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', f'/api/v1/audit/events/fatman/{fatman_name}')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def list_fatman_events(self, fatman_name: str, fatman_version: str) -> List[AuditLogEventDto]:
        response = self.lc_client.request_list('get', f'/api/v1/audit/events/fatman/{fatman_name}/{fatman_version}')
        return parse_dict_datamodels(response, AuditLogEventDto)

    def filter_events(self, 
        related_to_user: bool, 
        fatman_name: Optional[str], 
        fatman_version: Optional[str],
    ) -> List[AuditLogEventDto]:
        if related_to_user:
            if fatman_name and fatman_version:
                return self.list_user_fatman_events(fatman_name, fatman_version)
            elif fatman_name:
                return self.list_user_fatman_family_events(fatman_name)
            else:
                return self.list_user_events()
        else:
            if fatman_name and fatman_version:
                return self.list_fatman_events(fatman_name, fatman_version)
            elif fatman_name:
                return self.list_fatman_family_events(fatman_name)
            else:
                return self.list_all_events()
