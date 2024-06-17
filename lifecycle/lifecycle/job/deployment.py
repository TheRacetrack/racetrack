from typing import List, Optional
import uuid
from datetime import timedelta

from lifecycle.config import Config
from lifecycle.django.registry import models
from lifecycle.django.registry.database import db_access
from lifecycle.job.dto_converter import deployment_model_to_dto, job_model_to_dto
from lifecycle.job.models_registry import read_job_model
from racetrack_commons.entities.dto import DeploymentDto, DeploymentStatus
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.manifest.manifest import Manifest
from racetrack_client.utils.time import now


@db_access
def create_deployment(
    manifest: Manifest,
    username: str,
    infrastructure_target: str,
) -> DeploymentDto:
    check_for_concurrent_deployments(manifest)

    deployment_id = str(uuid.uuid4())
    deployment = models.Deployment(
        id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS.value,
        create_time=now(),
        update_time=now(),
        manifest=manifest.origin_yaml_,
        job_name=manifest.name,
        job_version=manifest.version,
        deployed_by=username,
        infrastructure_target=infrastructure_target,
    )
    deployment.save()
    return deployment_model_to_dto(deployment)


def check_for_concurrent_deployments(manifest: Manifest):
    update_time_after = now() - timedelta(minutes=1)
    deployments_queryset = models.Deployment.objects.filter(
        status=DeploymentStatus.IN_PROGRESS.value,
        job_name=manifest.name,
        job_version=manifest.version,
        update_time__gte=update_time_after,
    )

    ongoing_deployments = list(deployments_queryset)
    if ongoing_deployments:
        ongoing = ongoing_deployments[0]
        raise RuntimeError(f'There\'s already ongoing deployment of job {manifest.name} {manifest.version}, '
                           f'recently updated at {ongoing.update_time}')


@db_access
def check_deployment_result(deploy_id: str, config: Config) -> DeploymentDto:
    """Find deployment by ID and return its current status"""
    try:
        deployment = models.Deployment.objects.get(id=deploy_id)
        dto = deployment_model_to_dto(deployment)
        if deployment.status == DeploymentStatus.DONE.value:
            try:
                job_model = read_job_model(deployment.job_name, deployment.job_version)
                dto.job = job_model_to_dto(job_model, config)
            except EntityNotFound:
                pass
        return dto
    except models.Deployment.DoesNotExist:
        raise EntityNotFound(f'deployment with ID {deploy_id} was not found')


@db_access
def list_recent_deployments(limit: int) -> List[DeploymentDto]:
    deployment_models = models.Deployment.objects.all().order_by('-update_time')[:limit]
    return [deployment_model_to_dto(m) for m in deployment_models]


@db_access
def list_deployments_by_status(status: str) -> List[models.Deployment]:
    deployments_queryset = models.Deployment.objects.filter(status=status)
    return list(deployments_queryset)


@db_access
def save_deployment_result(
    deployment_id: str,
    status: DeploymentStatus,
    error: Optional[str] = None,
):
    """Save the result of the deployment in the database"""
    deployment = models.Deployment.objects.get(id=deployment_id)
    deployment.status = status.value
    if error:
        deployment.error = error
    else:
        deployment.error = None
        deployment.phase = None
    deployment.update_time = now()
    deployment.save()


@db_access
def save_deployment_build_logs(deployment_id: str, build_logs: str):
    deployment = models.Deployment.objects.get(id=deployment_id)
    deployment.build_logs = build_logs
    deployment.update_time = now()
    deployment.save()


@db_access
def save_deployment_phase(deployment_id: str, phase: str):
    try:
        deployment = models.Deployment.objects.get(id=deployment_id)
    except models.Deployment.DoesNotExist:
        raise EntityNotFound(f'deployment with ID {deployment_id} was not found')
    deployment.phase = phase
    deployment.update_time = now()
    deployment.save()


@db_access
def save_deployment_warnings(deployment_id: str, warnings: str):
    try:
        deployment = models.Deployment.objects.get(id=deployment_id)
    except models.Deployment.DoesNotExist:
        raise EntityNotFound(f'deployment with ID {deployment_id} was not found')
    deployment.warnings = f'{deployment.warnings},\n{warnings}' if deployment.warnings else warnings
    deployment.update_time = now()
    deployment.save()


@db_access
def save_deployment_image_name(deployment_id: Optional[str], image_name: str):
    if not deployment_id:
        return
    deployment = models.Deployment.objects.get(id=deployment_id)
    deployment.image_name = image_name
    deployment.update_time = now()
    deployment.save()
