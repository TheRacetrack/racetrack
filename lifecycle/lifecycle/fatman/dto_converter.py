import json
from lifecycle.config import Config
from lifecycle.django.registry import models
from lifecycle.fatman.pub import get_fatman_pub_url
from racetrack_client.manifest.load import parse_manifest_or_empty
from racetrack_client.utils.time import datetime_to_timestamp
from racetrack_commons.entities.dto import AuditLogEventDto, PublicEndpointRequestDto, EscDto
from racetrack_commons.entities.dto import FatmanDto, FatmanFamilyDto, DeploymentDto


def fatman_family_model_to_dto(model: models.FatmanFamily) -> FatmanFamilyDto:
    return FatmanFamilyDto(
        id=model.id,
        name=model.name,
    )


def fatman_model_to_dto(model: models.Fatman, config: Config) -> FatmanDto:
    return FatmanDto(
        id=model.id,
        name=model.name,
        version=model.version,
        status=model.status,
        create_time=datetime_to_timestamp(model.create_time),
        update_time=datetime_to_timestamp(model.update_time),
        manifest=parse_manifest_or_empty(model.manifest),
        internal_name=model.internal_name,
        pub_url=get_fatman_pub_url(model.name, model.version, config),
        error=model.error,
        image_tag=model.image_tag,
        deployed_by=model.deployed_by,
        last_call_time=datetime_to_timestamp(model.last_call_time) if model.last_call_time is not None else None,
        infrastructure_target=model.infrastructure_target,
    )


def deployment_model_to_dto(model: models.Deployment) -> DeploymentDto:
    return DeploymentDto(
        id=model.id,
        status=model.status,
        error=model.error,
        fatman=None,
        deployed_by=model.deployed_by,
        phase=model.phase,
        image_name=model.image_name,
        infrastructure_target=model.infrastructure_target,
    )


def esc_model_to_dto(model: models.Esc) -> EscDto:
    return EscDto(
        id=model.id,
        name=model.name,
    )


def public_endpoint_request_model_to_dto(model: models.PublicEndpointRequest) -> PublicEndpointRequestDto:
    return PublicEndpointRequestDto(
        fatman_name=model.fatman.name,
        fatman_version=model.fatman.version,
        endpoint=model.endpoint,
        active=model.active,
    )


def audit_log_event_to_dto(model: models.AuditLogEvent) -> AuditLogEventDto:
    properties = json.loads(model.properties) if model.properties else None
    return AuditLogEventDto(
        id=model.id,
        version=model.version,
        timestamp=datetime_to_timestamp(model.timestamp),
        event_type=model.event_type,
        properties=properties,
        username_executor=model.username_executor,
        username_subject=model.username_subject,
        fatman_name=model.fatman_name,
        fatman_version=model.fatman_version,
    )
