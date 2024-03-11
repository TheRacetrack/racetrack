import json

from lifecycle.config import Config
from lifecycle.django.registry import models
from lifecycle.job.pub import get_job_pub_url
from racetrack_client.manifest.load import parse_manifest_or_empty
from racetrack_client.utils.time import datetime_to_timestamp
from racetrack_commons.entities.dto import AuditLogEventDto, PublicEndpointRequestDto, EscDto, AsyncJobCallDto
from racetrack_commons.entities.dto import JobDto, JobFamilyDto, DeploymentDto


def job_family_model_to_dto(model: models.JobFamily) -> JobFamilyDto:
    return JobFamilyDto(
        id=model.id,
        name=model.name,
    )


def job_model_to_dto(model: models.Job, config: Config) -> JobDto:
    return JobDto(
        id=model.id,
        name=model.name,
        version=model.version,
        status=model.status,
        create_time=datetime_to_timestamp(model.create_time),
        update_time=datetime_to_timestamp(model.update_time),
        manifest=parse_manifest_or_empty(model.manifest),
        manifest_yaml=model.manifest,
        internal_name=model.internal_name,
        pub_url=get_job_pub_url(model.name, model.version, config),
        error=model.error,
        notice=model.notice,
        image_tag=model.image_tag,
        deployed_by=model.deployed_by,
        last_call_time=datetime_to_timestamp(model.last_call_time) if model.last_call_time is not None else None,
        infrastructure_target=model.infrastructure_target,
        replica_internal_names=model.replica_internal_names.split(',') if model.replica_internal_names else [],
        job_type_version=model.job_type_version,
    )


def deployment_model_to_dto(model: models.Deployment) -> DeploymentDto:
    return DeploymentDto(
        id=model.id,
        status=model.status,
        error=model.error,
        job=None,
        deployed_by=model.deployed_by,
        phase=model.phase,
        image_name=model.image_name,
        infrastructure_target=model.infrastructure_target,
        manifest_yaml=model.manifest,
        create_time=datetime_to_timestamp(model.create_time),
        update_time=datetime_to_timestamp(model.update_time),
        job_name=model.job_name,
        job_version=model.job_version,
    )


def esc_model_to_dto(model: models.Esc) -> EscDto:
    return EscDto(
        id=model.id,
        name=model.name,
    )


def public_endpoint_request_model_to_dto(model: models.PublicEndpointRequest) -> PublicEndpointRequestDto:
    return PublicEndpointRequestDto(
        job_name=model.job.name,
        job_version=model.job.version,
        endpoint=model.endpoint,
        active=model.active,
    )


def audit_log_event_to_dto(model: models.AuditLogEvent) -> AuditLogEventDto:
    properties = json.loads(model.properties) if model.properties else {}
    return AuditLogEventDto(
        id=model.id,
        version=model.version,
        timestamp=datetime_to_timestamp(model.timestamp),
        event_type=model.event_type,
        properties=properties,
        username_executor=model.username_executor,
        username_subject=model.username_subject,
        job_name=model.job_name,
        job_version=model.job_version,
    )


def async_job_call_to_dto(model: models.AsyncJobCall) -> AsyncJobCallDto:
    return AsyncJobCallDto(
        id=model.id,
        status=model.status,
        started_at=model.started_at,
        ended_at=model.ended_at,
        error=model.error,
        job_name=model.job_name,
        job_version=model.job_version,
        job_path=model.job_path,
        url=model.url,
        method=model.method,
        request_data=model.request_data,
        response_data=model.response_data or b'',
        response_json=model.response_json,
        response_status_code=model.response_status_code,
        attempts=model.attempts,
        pub_instance=model.pub_instance,
    )
