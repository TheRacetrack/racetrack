from typing import List

from lifecycle.django.registry import models
from lifecycle.django.registry.database import db_access
from lifecycle.job.dto_converter import public_endpoint_request_model_to_dto
from lifecycle.job.models_registry import read_job_model, resolve_job_model
from racetrack_commons.entities.dto import PublicEndpointRequestDto


@db_access
def read_active_job_public_endpoints(
    job_name: str, job_version: str
) -> List[PublicEndpointRequestDto]:
    """
    Get list of active public endpoints that can be accessed
    without authentication for a particular Job
    :param job_version: Exact job_version or an alias ("latest" or wildcard)
    """
    job_model = resolve_job_model(job_name, job_version)
    resolved_version = job_model.version

    queryset = models.PublicEndpointRequest.objects.filter(
        job__name=job_name, job__version=resolved_version, active=True
    )
    return [public_endpoint_request_model_to_dto(model) for model in queryset]


@db_access
def create_job_public_endpoint_if_not_exist(
    job_name: str, job_version: str, endpoint: str
) -> models.PublicEndpointRequest:
    job_model = read_job_model(job_name, job_version)
    try:
        return models.PublicEndpointRequest.objects.get(
            job=job_model, endpoint=endpoint
        )
    except models.PublicEndpointRequest.DoesNotExist:
        new_model = models.PublicEndpointRequest(
            job=job_model,
            endpoint=endpoint,
            active=False,
        )
        new_model.save()
        return new_model
