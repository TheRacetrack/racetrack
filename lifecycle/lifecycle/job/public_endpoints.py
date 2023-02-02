from typing import List

from lifecycle.django.registry import models
from lifecycle.django.registry.database import db_access
from lifecycle.fatman.dto_converter import public_endpoint_request_model_to_dto
from lifecycle.fatman.models_registry import read_fatman_model, resolve_fatman_model
from racetrack_commons.entities.dto import PublicEndpointRequestDto


@db_access
def read_active_fatman_public_endpoints(
    fatman_name: str, fatman_version: str
) -> List[PublicEndpointRequestDto]:
    """
    Get list of active public endpoints that can be accessed
    without authentication for a particular Fatman
    :param fatman_version: Exact fatman version or an alias ("latest" or wildcard)
    """
    fatman_model = resolve_fatman_model(fatman_name, fatman_version)
    resolved_version = fatman_model.version

    queryset = models.PublicEndpointRequest.objects.filter(
        fatman__name=fatman_name, fatman__version=resolved_version, active=True
    )
    return [public_endpoint_request_model_to_dto(model) for model in queryset]


@db_access
def create_fatman_public_endpoint_if_not_exist(
    fatman_name: str, fatman_version: str, endpoint: str
) -> models.PublicEndpointRequest:
    fatman_model = read_fatman_model(fatman_name, fatman_version)
    try:
        return models.PublicEndpointRequest.objects.get(
            fatman=fatman_model, endpoint=endpoint
        )
    except models.PublicEndpointRequest.DoesNotExist:
        new_model = models.PublicEndpointRequest(
            fatman=fatman_model,
            endpoint=endpoint,
            active=False,
        )
        new_model.save()
        return new_model
