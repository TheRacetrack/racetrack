from typing import Optional

from lifecycle.config import Config
from lifecycle.deployer.deploy import build_and_provision, provision_job
from lifecycle.deployer.deployers import get_job_deployer
from lifecycle.deployer.secrets import JobSecrets
from lifecycle.job.deployment import create_deployment, save_deployment_phase, save_deployment_result
from lifecycle.job.registry import decommission_job_infrastructure, read_job
from lifecycle.django.registry import models
from racetrack_client.log.context_error import wrap_context
from racetrack_client.manifest.manifest import Manifest
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.entities.dto import DeploymentStatus, JobDto


def redeploy_job(
    job_name: str,
    job_version: str,
    config: Config,
    plugin_engine: PluginEngine,
    deployer_username: str,
    auth_subject: Optional[models.AuthSubject],
):
    """Deploy (rebuild and reprovision) Job once again without knowing secrets"""
    job = read_job(job_name, job_version, config)
    manifest = job.manifest
    assert job.manifest is not None, "job doesn't have Manifest data specified"

    infra_target = job.infrastructure_target
    deployment = create_deployment(manifest, deployer_username, infra_target)
    try:
        job_secrets = _retrieve_job_secrets(config, manifest, plugin_engine, job)

        with wrap_context('redeploying job'):
            build_and_provision(
                config, manifest, job_secrets, deployment,
                build_context=None,
                auth_subject=auth_subject,
                previous_job=job,
                plugin_engine=plugin_engine,
            )

        save_deployment_result(deployment.id, DeploymentStatus.DONE)

    except BaseException as e:
        save_deployment_result(deployment.id, DeploymentStatus.FAILED, error=str(e))
        raise e


def reprovision_job(
    job_name: str,
    job_version: str,
    config: Config,
    plugin_engine: PluginEngine,
    deployer_username: str,
    auth_subject: Optional[models.AuthSubject],
):
    """Reprovision already built Job image once again to a cluster"""
    job = read_job(job_name, job_version, config)
    manifest = job.manifest
    assert job.manifest is not None, "job doesn't have Manifest data specified"
    assert job.image_tag is not None, "latest image tag is unknown"

    infra_target = job.infrastructure_target
    deployment = create_deployment(manifest, deployer_username, infra_target)
    try:
        if manifest.secret_runtime_env_file:
            job_secrets = _retrieve_job_secrets(config, manifest, plugin_engine, job)
        else:
            job_secrets = JobSecrets(git_credentials=None, secret_build_env={}, secret_runtime_env={})

        with wrap_context('reprovisioning job'):
            provision_job(
                config, manifest, job.image_tag, job_secrets.secret_build_env,
                job_secrets.secret_runtime_env, deployment,
                auth_subject, None, plugin_engine,
            )

        save_deployment_result(deployment.id, DeploymentStatus.DONE)

    except BaseException as e:
        save_deployment_result(deployment.id, DeploymentStatus.FAILED, error=str(e))
        raise e


def move_job(
    job_name: str,
    job_version: str,
    new_infra_target: str,
    config: Config,
    plugin_engine: PluginEngine,
    deployer_username: str,
    auth_subject: Optional[models.AuthSubject],
):
    """Move job from one infrastructure target to another"""
    job = read_job(job_name, job_version, config)
    manifest = job.manifest
    old_infra_target = job.infrastructure_target
    assert job.manifest is not None, "job doesn't have Manifest data specified"
    assert job.image_tag is not None, "job's image tag is unknown"
    assert new_infra_target, "infrastructure target has to be specified"
    assert new_infra_target != old_infra_target, "new infrastructure target has to be different from the current one"

    deployment = create_deployment(manifest, deployer_username, new_infra_target)
    try:
        if manifest.secret_runtime_env_file:
            job_secrets = _retrieve_job_secrets(config, manifest, plugin_engine, job)
        else:
            job_secrets = JobSecrets(git_credentials=None, secret_build_env={}, secret_runtime_env={})

        with wrap_context('deploying job to a new infrastructure'):
            provision_job(
                config, manifest, job.image_tag, job_secrets.secret_build_env,
                job_secrets.secret_runtime_env, deployment,
                auth_subject, None, plugin_engine
            )

        with wrap_context('deleting job from a former infrastructure'):
            save_deployment_phase(deployment.id, 'deleting job from a former infrastructure')
            decommission_job_infrastructure(
                job.name, job.version, old_infra_target, config, deployer_username, plugin_engine
            )

        save_deployment_result(deployment.id, DeploymentStatus.DONE)

    except BaseException as e:
        save_deployment_result(deployment.id, DeploymentStatus.FAILED, error=str(e))
        raise e


def _retrieve_job_secrets(config: Config, manifest: Manifest, plugin_engine: PluginEngine, job: JobDto) -> JobSecrets:
    with wrap_context('retrieving job secrets'):
        job_deployer = get_job_deployer(plugin_engine, job.infrastructure_target)
        return job_deployer.get_job_secrets(manifest.name, manifest.version)
