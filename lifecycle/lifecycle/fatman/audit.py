import json
from typing import Dict, List, Optional

from django.db.models import Q

from lifecycle.django.registry import models
from lifecycle.django.registry.database import db_access
from lifecycle.fatman.dto_converter import audit_log_event_to_dto
from racetrack_client.utils.time import now
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.audit import AuditLogEventType
from racetrack_commons.entities.dto import AuditLogEventDto

logger = get_logger(__name__)


class AuditLogger:
    def log_event(
        self,
        event_type: AuditLogEventType,
        properties: Dict = None,
        username_executor: str = None,
        username_subject: str = None,
        fatman_name: str = None,
        fatman_version: str = None,
    ):
        timestamp = now()
        properties_json = json.dumps(properties) if properties else None
        ale = models.AuditLogEvent(
            timestamp=timestamp,
            event_type=event_type.value,
            properties=properties_json,
            username_executor=username_executor,
            username_subject=username_subject,
            fatman_name=fatman_name,
            fatman_version=fatman_version,
        )
        ale.save()

        traits = properties or {}
        traits['username_executor'] = username_executor
        traits['username_subject'] = username_subject
        traits['fatman_name'] = fatman_name
        traits['fatman_version'] = fatman_version
        traits_str = ', '.join((f'{k}={v}' for k, v in traits.items() if v))
        logger.info(f'Audit log event saved: {event_type.value}, {traits_str}')


@db_access
def read_audit_log_user_events(
    username: Optional[str] = None,
    fatman_name: Optional[str] = None,
    fatman_version: Optional[str] = None,
) -> List[AuditLogEventDto]:
    """
    Get list of active public endpoints that can be accessed
    without authentication for a particular Fatman
    :param fatman_version: Exact fatman version or an alias ("latest" or wildcard)
    """
    username_filter = Q(username_executor=username) | Q(username_subject=username) if username else Q()
    fatman_name_filter = Q(fatman_name=fatman_name) if fatman_name else Q()
    fatman_version_filter = Q(fatman_version=fatman_version) if fatman_version else Q()
    queryset = models.AuditLogEvent.objects.filter(
        username_filter & fatman_name_filter & fatman_version_filter
    ).order_by('-timestamp')[:100]
    return [audit_log_event_to_dto(model) for model in queryset]
