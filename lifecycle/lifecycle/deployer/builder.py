import threading
from typing import Optional, Dict

import backoff

from lifecycle.config import Config
from lifecycle.deployer.infra_target import determine_infrastructure_name
from lifecycle.deployer.secrets import JobSecrets
from lifecycle.django.registry.database import db_access
from lifecycle.job.deployment import create_deployment, save_deployment_build_logs, save_deployment_image_name, save_deployment_result, save_deployment_phase
from racetrack_client.client_config.client_config import Credentials
from racetrack_client.client.env import SecretVars
from racetrack_client.utils.request import parse_response_object, Requests, RequestError
from racetrack_client.utils.datamodel import datamodel_to_dict
from racetrack_client.utils.time import now
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest import Manifest
from racetrack_commons.deploy.image import get_job_image
from racetrack_commons.entities.dto import DeploymentDto, DeploymentStatus
from racetrack_commons.plugin.engine import PluginEngine

logger = get_logger(__name__)


def build_job(
    config: Config,
    manifest: Manifest,
    job_secrets: JobSecrets,
    deployment: DeploymentDto,
    build_context: Optional[str],
    tag: str,
):
    with wrap_context('building an image'):
        save_deployment_phase(deployment.id, 'building image')
        _send_image_build_request(config, manifest, job_secrets.git_credentials,
                                  job_secrets.secret_build_env, tag, deployment, build_context)


def _send_image_build_request(
    config: Config,
    manifest: Manifest,
    git_credentials: Optional[Credentials],
    secret_build_env: Dict[str, str],
    tag: str,
    deployment: DeploymentDto,
    build_context: Optional[str],
):
    """
    Send request to Image Builder API in order to build image at given workspace
    """
    logger.info(f'building a job by image-builder, deployment ID: {deployment.id}')
    # see `image_builder.api._setup_api_endpoints`
    r = Requests.post(
        f'{config.image_builder_url}/api/v1/build',
        json=_build_image_request_payload(manifest, git_credentials, secret_build_env, tag, build_context, deployment),
    )
    response = parse_response_object(r, 'Image builder API error')
    build_logs: str = response['logs']
    image_name = get_job_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag)
    save_deployment_build_logs(deployment.id, build_logs)
    save_deployment_image_name(deployment.id, image_name)
    error: str = response['error']
    if error:
        raise RuntimeError(error)
    logger.info(f'job image {image_name} has been built, deployment ID: {deployment.id}')


def _build_image_request_payload(
    manifest: Manifest,
    git_credentials: Optional[Credentials],
    secret_build_env: Dict[str, str],
    tag: str,
    build_context: Optional[str],
    deployment: DeploymentDto,
) -> Dict:
    return {
        "manifest": datamodel_to_dict(manifest),
        "git_credentials": git_credentials.dict() if git_credentials is not None else None,
        "secret_build_env": secret_build_env,
        "tag": tag,
        "build_context": build_context,
        "deployment_id": deployment.id,
    }


@db_access
def build_job_in_background(
    config: Config,
    manifest: Manifest,
    git_credentials: Optional[Credentials],
    secret_vars: SecretVars,
    build_context: Optional[str],
    username: str,
    plugin_engine: PluginEngine,
) -> str:
    infra_target = determine_infrastructure_name(config, plugin_engine, manifest)
    deployment = create_deployment(manifest, username, infra_target)
    
    logger.info(f'started building job {deployment.id} in background')
    args = (config, manifest, git_credentials, secret_vars, deployment, build_context)
    thread = threading.Thread(target=_build_job_saving_result, args=args, daemon=True)
    thread.start()
    return deployment.id


@db_access
def _build_job_saving_result(
    config: Config,
    manifest: Manifest,
    git_credentials: Optional[Credentials],
    secret_vars: SecretVars,
    deployment: DeploymentDto,
    build_context: Optional[str],
):
    """Deploy a Job storing its faulty or successful result in DB"""
    try:
        wait_for_image_builder_ready(config)

        tag = now().strftime('%Y-%m-%dT%H%M%S')
        job_secrets = JobSecrets(
            git_credentials=git_credentials,
            secret_build_env=secret_vars.build_env,
            secret_runtime_env=secret_vars.runtime_env,
        )

        build_job(config, manifest, job_secrets, deployment, build_context, tag)
        save_deployment_result(deployment.id, DeploymentStatus.DONE)
    except BaseException as e:
        log_exception(e)
        save_deployment_result(deployment.id, DeploymentStatus.FAILED, error=str(e))


@backoff.on_exception(backoff.fibo, RequestError, max_value=3, max_time=30, jitter=None)
def wait_for_image_builder_ready(config: Config):
    Requests.get(f'{config.image_builder_url}/health').raise_for_status()
