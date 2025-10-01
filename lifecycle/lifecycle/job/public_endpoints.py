from typing import List

from lifecycle.database.schema import tables
from lifecycle.database.schema.dto_converter import public_endpoint_request_record_to_dto
from lifecycle.database.table_model import new_uuid
from lifecycle.job.models_registry import read_job_model, resolve_job_model
from lifecycle.server.cache import LifecycleCache
from racetrack_client.log.errors import EntityNotFound
from racetrack_commons.entities.dto import PublicEndpointRequestDto


def read_active_job_public_endpoints(
    job_name: str, job_version: str
) -> List[PublicEndpointRequestDto]:
    """
    Get list of active public endpoints that can be accessed
    without authentication for a particular Job
    :param job_version: Exact job_version or an alias ("latest" or wildcard)
    """
    job_model = resolve_job_model(job_name, job_version)
    mapper = LifecycleCache.record_mapper()
    records: list[tables.PublicEndpointRequest] = mapper.find_many(
        tables.PublicEndpointRequest,
        job_id=job_model.id,
        active=True,
    )
    return [public_endpoint_request_record_to_dto(record) for record in records]


def read_job_model_public_endpoints(
    job_model: tables.Job,
) -> List[str]:
    records = LifecycleCache.record_mapper().find_many(
        tables.PublicEndpointRequest, job_id=job_model.id, active=True,
    )
    return [record.endpoint for record in records]


def create_job_public_endpoint_if_not_exist(
    job_name: str, job_version: str, endpoint: str
) -> tables.PublicEndpointRequest:
    job_model = read_job_model(job_name, job_version)
    mapper = LifecycleCache.record_mapper()
    try:
        return mapper.find_one(
            tables.PublicEndpointRequest, job_id=job_model.id, endpoint=endpoint,
        )
    except EntityNotFound:
        new_record = tables.PublicEndpointRequest(
            id=new_uuid(),
            job_id=job_model.id,
            endpoint=endpoint,
            active=False,
        )
        mapper.create(new_record)
        return new_record
