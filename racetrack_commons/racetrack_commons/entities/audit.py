from enum import Enum

from racetrack_commons.entities.dto import AuditLogEventDto


class AuditLogEventType(Enum):
    FATMAN_DEPLOYED = 'fatman_deployed'
    FATMAN_REDEPLOYED = 'fatman_redeployed'
    FATMAN_DELETED = 'fatman_deleted'
    

def explain_audit_log_event(ale: AuditLogEventDto) -> str:
    """Generate a human-readable explanation of an audit log event."""
    if ale.event_type == AuditLogEventType.FATMAN_DEPLOYED.value:
        return f'Fatman {ale.fatman_name} {ale.fatman_version} deployed by {ale.username_executor}'
    elif ale.event_type == AuditLogEventType.FATMAN_REDEPLOYED.value:
        owner_info = f'(owned by {ale.username_subject})' if ale.username_subject else ''
        return f'Fatman {ale.fatman_name} {ale.fatman_version} {owner_info} redeployed by {ale.username_executor}'
    elif ale.event_type == AuditLogEventType.FATMAN_DELETED.value:
        owner_info = f'(owned by {ale.username_subject})' if ale.username_subject else ''
        return f'Fatman {ale.fatman_name} {ale.fatman_version} {owner_info} deleted by {ale.username_executor}'
    else:
        raise RuntimeError(f'Unknown audit log event type: {ale.event_type}')
