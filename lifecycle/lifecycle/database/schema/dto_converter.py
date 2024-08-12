from lifecycle.database.table_model import parse_json_column
from racetrack_client.manifest.load import parse_manifest_or_empty
from racetrack_client.utils.time import datetime_to_timestamp
from racetrack_commons.entities.dto import JobDto, JobFamilyDto, DeploymentDto
from lifecycle.config import Config
from lifecycle.job.pub import get_job_pub_url
from lifecycle.database.schema import tables


def job_family_record_to_dto(model: tables.JobFamily) -> JobFamilyDto:
    return JobFamilyDto(
        id=model.id,
        name=model.name,
    )


def job_record_to_dto(model: tables.Job, config: Config) -> JobDto:
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
        infrastructure_stats=parse_json_column(model.infrastructure_stats) or {},
    )