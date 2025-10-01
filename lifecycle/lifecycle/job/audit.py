import json
from typing import Any

from lifecycle.database.condition_builder import QueryCondition
from lifecycle.database.schema import tables
from lifecycle.database.schema.dto_converter import audit_log_event_record_to_dto
from lifecycle.database.table_model import new_uuid
from lifecycle.server.cache import LifecycleCache
from racetrack_client.utils.time import now
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.audit import AuditLogEventType
from racetrack_commons.entities.dto import AuditLogEventDto

logger = get_logger(__name__)


class AuditLogger:
    def log_event(
        self,
        event_type: AuditLogEventType,
        properties: dict[str, Any] | None = None,
        username_executor: str | None = None,
        username_subject: str | None = None,
        job_name: str | None = None,
        job_version: str | None = None,
    ):
        timestamp = now()
        properties_json = json.dumps(properties) if properties else None
        ale = tables.AuditLogEvent(
            id=new_uuid(),
            version=1,
            timestamp=timestamp,
            event_type=event_type.value,
            properties=properties_json,
            username_executor=username_executor,
            username_subject=username_subject,
            job_name=job_name,
            job_version=job_version,
        )
        LifecycleCache.record_mapper().create(ale)

        traits = properties or {}
        traits['username_executor'] = username_executor
        traits['username_subject'] = username_subject
        traits['job_name'] = job_name
        traits['job_version'] = job_version
        traits_str = ', '.join((f'{k}={v}' for k, v in traits.items() if v))
        logger.info(f'Audit log event saved: {event_type.value}, {traits_str}')


def read_audit_log_user_events(
    username: str | None = None,
    job_name: str | None = None,
    job_version: str | None = None,
) -> list[AuditLogEventDto]:
    """
    Get list of active public endpoints that can be accessed
    without authentication for a particular Job
    :param username: Username to filter the events
    :param job_name: Name of the job to filter the events
    :param job_version: Exact job version or an alias ("latest" or wildcard)
    """
    mapper = LifecycleCache.record_mapper()
    placeholder = mapper.placeholder
    username_filter: QueryCondition = QueryCondition.operator_or(
        QueryCondition(f'"username_executor" = {placeholder}', username),
        QueryCondition(f'"username_subject" = {placeholder}', username),
    ) if username else QueryCondition.empty()
    job_name_filter = QueryCondition(f'"job_name" = {placeholder}', job_name) if job_name else QueryCondition.empty()
    job_version_filter = QueryCondition(f'"job_version" = {placeholder}', job_version) if job_version else QueryCondition.empty()
    query_condition = QueryCondition.operator_and(username_filter, job_name_filter, job_version_filter)
    records = mapper.filter(
        tables.AuditLogEvent, query_condition, order_by=['-timestamp'], limit=100,
    )
    return [audit_log_event_record_to_dto(model) for model in records]
