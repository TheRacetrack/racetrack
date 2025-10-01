import uuid
from datetime import timedelta

from lifecycle.config import Config
from lifecycle.database.condition_builder import QueryCondition
from lifecycle.database.schema import tables
from lifecycle.database.schema.dto_converter import deployment_record_to_dto, job_record_to_dto
from lifecycle.job.models_registry import read_job_model
from lifecycle.server.cache import LifecycleCache
from racetrack_commons.entities.dto import DeploymentDto, DeploymentStatus
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.manifest.manifest import Manifest
from racetrack_client.utils.time import now


def create_deployment(
    manifest: Manifest,
    username: str,
    infrastructure_target: str,
) -> DeploymentDto:
    check_for_concurrent_deployments(manifest)

    deployment_id = str(uuid.uuid4())
    deployment = tables.Deployment(
        id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS.value,
        create_time=now(),
        update_time=now(),
        manifest=manifest.origin_yaml_ or '',
        error=None,
        job_name=manifest.name,
        job_version=manifest.version,
        deployed_by=username,
        build_logs=None,
        phase=None,
        image_name=None,
        infrastructure_target=infrastructure_target,
        warnings=None,
    )
    LifecycleCache.record_mapper().create(deployment)
    return deployment_record_to_dto(deployment)


def check_for_concurrent_deployments(manifest: Manifest):
    mapper = LifecycleCache.record_mapper()
    placeholder = mapper.placeholder
    update_time_after = now() - timedelta(minutes=1)
    filter_condition = QueryCondition(
        f'"status" = {placeholder} and "job_name" = {placeholder} and "job_version" = {placeholder} and "update_time" >= {placeholder}',
        DeploymentStatus.IN_PROGRESS.value, manifest.name, manifest.version, update_time_after
    )
    ongoing_deployments = mapper.filter(tables.Deployment, condition=filter_condition)

    if ongoing_deployments:
        ongoing = ongoing_deployments[0]
        raise RuntimeError(f'There\'s already ongoing deployment of job {manifest.name} {manifest.version}, '
                           f'recently updated at {ongoing.update_time}')


def check_deployment_result(deploy_id: str, config: Config) -> DeploymentDto:
    """Find deployment by ID and return its current status"""
    try:
        mapper = LifecycleCache.record_mapper()
        deployment = mapper.find_one(tables.Deployment, id=deploy_id)
        dto = deployment_record_to_dto(deployment)
        if deployment.status == DeploymentStatus.DONE.value:
            try:
                job_model = read_job_model(deployment.job_name, deployment.job_version)
                dto.job = job_record_to_dto(job_model, config)
            except EntityNotFound:
                pass
        return dto
    except EntityNotFound:
        raise EntityNotFound(f'deployment with ID {deploy_id} was not found')


def list_recent_deployments(limit: int) -> list[DeploymentDto]:
    mapper = LifecycleCache.record_mapper()
    deployment_models = mapper.list_all(tables.Deployment, order_by=['-update_time'], limit=limit)
    return [deployment_record_to_dto(m) for m in deployment_models]


def list_deployments_by_status(status: str) -> list[tables.Deployment]:
    mapper = LifecycleCache.record_mapper()
    return mapper.find_many(tables.Deployment, status=status)


def save_deployment_result(
    deployment_id: str,
    status: DeploymentStatus,
    error: str | None = None,
):
    """Save the result of the deployment in the database"""
    mapper = LifecycleCache.record_mapper()
    deployment = mapper.find_one(tables.Deployment, id=deployment_id)
    deployment.status = status.value
    if error:
        deployment.error = error
    else:
        deployment.error = None
        deployment.phase = None
    deployment.update_time = now()
    mapper.update(deployment)


def save_deployment_build_logs(deployment_id: str, build_logs: str):
    mapper = LifecycleCache.record_mapper()
    deployment = mapper.find_one(tables.Deployment, id=deployment_id)
    deployment.build_logs = build_logs
    deployment.update_time = now()
    mapper.update(deployment)


def save_deployment_phase(deployment_id: str, phase: str):
    mapper = LifecycleCache.record_mapper()
    try:
        deployment = mapper.find_one(tables.Deployment, id=deployment_id)
    except EntityNotFound:
        raise EntityNotFound(f'deployment with ID {deployment_id} was not found')
    deployment.phase = phase
    deployment.update_time = now()
    mapper.update(deployment)


def save_deployment_warnings(deployment_id: str, warnings: str):
    mapper = LifecycleCache.record_mapper()
    try:
        deployment = mapper.find_one(tables.Deployment, id=deployment_id)
    except EntityNotFound:
        raise EntityNotFound(f'deployment with ID {deployment_id} was not found')
    deployment.warnings = f'{deployment.warnings}\n{warnings}' if deployment.warnings else warnings
    deployment.update_time = now()
    mapper.update(deployment)


def save_deployment_image_name(deployment_id: str | None, image_name: str):
    mapper = LifecycleCache.record_mapper()
    if not deployment_id:
        return
    deployment = mapper.find_one(tables.Deployment, id=deployment_id)
    deployment.image_name = image_name
    deployment.update_time = now()
    mapper.update(deployment)
