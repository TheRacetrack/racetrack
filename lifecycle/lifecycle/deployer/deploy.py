import logging
import threading
from typing import Optional
from lifecycle.deployer.infra_target import determine_infrastructure_name

from racetrack_client.client.env import SecretVars
from racetrack_client.client_config.client_config import Credentials
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest import Manifest
from racetrack_client.utils.time import now
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.entities.dto import DeploymentDto, DeploymentStatus, JobDto
from lifecycle.config import Config
from lifecycle.deployer.builder import build_job, wait_for_image_builder_ready
from lifecycle.deployer.deployers import get_job_deployer
from lifecycle.deployer.permissions import check_deploy_permissions
from lifecycle.deployer.provision import provision_job
from lifecycle.deployer.secrets import JobSecrets
from lifecycle.django.registry import models
from lifecycle.job.deployment import create_deployment, save_deployment_result
from lifecycle.job.models_registry import job_exists, find_deleted_job

logger = get_logger(__name__)


def deploy_new_job(
    config: Config,
    manifest: Manifest,
    git_credentials: Optional[Credentials],
    secret_vars: SecretVars,
    deployment: DeploymentDto,
    build_context: Optional[str],
    force: bool,
    auth_subject: models.AuthSubject,
    plugin_engine: PluginEngine,
):
    """Deploy (build and provision) new Job instance, providing secrets"""
    _protect_job_overwriting(manifest, force)
    check_deploy_permissions(auth_subject, manifest)

    with wrap_context('saving job secrets'):
        job_secrets = JobSecrets(
            git_credentials=git_credentials,
            secret_build_env=secret_vars.build_env,
            secret_runtime_env=secret_vars.runtime_env,
        )
        job_deployer = get_job_deployer(plugin_engine, deployment.infrastructure_target)
        try:
            job_deployer.save_job_secrets(manifest.name, manifest.version, job_secrets)
        except NotImplementedError:
            logging.warning(f'managing secrets is not supported on {deployment.infrastructure_target}')

    build_and_provision(
        config, manifest, job_secrets, deployment, build_context,
        auth_subject, None, plugin_engine,
    )


def build_and_provision(
    config: Config,
    manifest: Manifest,
    job_secrets: JobSecrets,
    deployment: DeploymentDto,
    build_context: Optional[str],
    auth_subject: Optional[models.AuthSubject],
    previous_job: Optional[JobDto],
    plugin_engine: PluginEngine,
):
    """Build a Job image from a manifest file and provision it (deploy to a cluster)"""
    tag = now().strftime(r'%Y-%m-%dT%H%M%S')
    build_job(config, manifest, job_secrets, deployment, build_context, tag)
    provision_job(
        config, manifest, tag, job_secrets.secret_build_env,
        job_secrets.secret_runtime_env, deployment,
        auth_subject, previous_job, plugin_engine,
    )


def deploy_job_in_background(
    config: Config,
    manifest: Manifest,
    git_credentials: Optional[Credentials],
    secret_vars: SecretVars,
    build_context: Optional[str],
    force: bool,
    plugin_engine: PluginEngine,
    username: str,
    auth_subject: models.AuthSubject,
) -> str:
    """
    Schedule deployment of a job in background
    :return: deployment ID
    """
    infra_target = determine_infrastructure_name(config, plugin_engine, manifest)
    deployment = create_deployment(manifest, username, infra_target)
    logger.info(f'starting deployment {deployment.id} in background')
    args = (config, manifest, git_credentials, secret_vars, deployment,
            build_context, force, plugin_engine, auth_subject)
    thread = threading.Thread(target=deploy_job_saving_result, args=args, daemon=True)
    thread.start()
    return deployment.id


def deploy_job_saving_result(
    config: Config,
    manifest: Manifest,
    git_credentials: Optional[Credentials],
    secret_vars: SecretVars,
    deployment: DeploymentDto,
    build_context: Optional[str],
    force: bool,
    plugin_engine: PluginEngine,
    auth_subject: models.AuthSubject,
):
    """Deploy a Job storing its faulty or successful result in DB"""
    try:
        wait_for_image_builder_ready(config)
        deploy_new_job(
            config, manifest, git_credentials, secret_vars, deployment,
            build_context, force, auth_subject, plugin_engine,
        )
        save_deployment_result(deployment.id, DeploymentStatus.DONE)
    except BaseException as e:
        log_exception(e)
        save_deployment_result(deployment.id, DeploymentStatus.FAILED, error=str(e))


def _protect_job_overwriting(manifest: Manifest, force: bool):
    if job_exists(manifest.name, manifest.version):
        if force:
            logger.info(f'overwriting job {manifest.name} v{manifest.version} due to force deployment')
            return

        raise RuntimeError(f'job {manifest.name} v{manifest.version} is already deployed. '
                           'Try deploying next version or use --force flag')

    else:
        trash_job = find_deleted_job(manifest.name, manifest.version)
        if trash_job is not None:
            if force:
                logger.info(f'deploying job {manifest.name} v{manifest.version} again due to force deployment')
                return

            raise RuntimeError(f'Job {manifest.name} v{manifest.version} has already been deployed and deleted. '
                               f'Can\'t claim it again to prevent accidental/hostile reusing.')
