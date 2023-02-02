from enum import Enum

from racetrack_commons.entities.dto import AuditLogEventDto


class AuditLogEventType(Enum):
    JOB_DEPLOYED = 'job_deployed'
    JOB_REDEPLOYED = 'job_redeployed'
    JOB_DELETED = 'job_deleted'
    

def explain_audit_log_event(ale: AuditLogEventDto) -> str:
    """Generate a human-readable explanation of an audit log event."""
    if ale.event_type == AuditLogEventType.JOB_DEPLOYED.value:
        return f'Job {ale.job_name} {ale.job_version} deployed by {ale.username_executor}'
    elif ale.event_type == AuditLogEventType.JOB_REDEPLOYED.value:
        owner_info = f'(owned by {ale.username_subject})' if ale.username_subject else ''
        return f'Job {ale.job_name} {ale.job_version} {owner_info} redeployed by {ale.username_executor}'
    elif ale.event_type == AuditLogEventType.JOB_DELETED.value:
        owner_info = f'(owned by {ale.username_subject})' if ale.username_subject else ''
        return f'Job {ale.job_name} {ale.job_version} {owner_info} deleted by {ale.username_executor}'
    else:
        raise RuntimeError(f'Unknown audit log event type: {ale.event_type}')
