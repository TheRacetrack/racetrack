from lifecycle.auth.authorize import grant_permission
from lifecycle.config import Config
from lifecycle.config.maintenance import ensure_no_maintenance
from lifecycle.deployer.deployers import get_job_deployer
from lifecycle.deployer.permissions import check_deploy_permissions
from lifecycle.django.registry import models
from lifecycle.job.audit import AuditLogger
from lifecycle.job.deployment import save_deployment_phase
from lifecycle.job.dto_converter import job_family_model_to_dto
from lifecycle.job.models_registry import create_job_family_if_not_exist, save_job_model, update_job
from lifecycle.job.public_endpoints import create_job_public_endpoint_if_not_exist
from lifecycle.monitor.monitors import check_job_condition
from lifecycle.server.metrics import metric_deployed_job
from racetrack_client.client.env import merge_env_vars
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest import Manifest
from racetrack_commons.plugin.call import safe_call
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.deploy.image import get_job_image
from racetrack_commons.deploy.job_type import JobType, load_job_type
from racetrack_commons.entities.audit import AuditLogEventType
from racetrack_commons.entities.dto import DeploymentDto, JobDto, JobStatus

logger = get_logger(__name__)


def provision_job(
    config: Config,
    manifest: Manifest,
    tag: str,
    secret_build_env: dict[str, str],
    secret_runtime_env: dict[str, str],
    deployment: DeploymentDto,
    auth_subject: models.AuthSubject | None,
    previous_job: JobDto | None,
    plugin_engine: PluginEngine,
) -> JobDto:
    """
    Deploy built Job to a cluster
    :param config: Lifecycle server configuration
    :param manifest: job's manifest
    :param tag: tag name of the docker image
    :param secret_build_env: dicionary of secret build environment variables
    :param secret_runtime_env: dictionary of secret runtime environment variables
    :param deployment: Deployment model data
    :param auth_subject: user attempting to provision a job
    :param previous_job: previous job version in case of redeploying
    :param plugin_engine: engine for calling hooks from the uploaded plugins
    """
    ensure_no_maintenance()
    if auth_subject is not None:
        check_deploy_permissions(auth_subject, manifest)

    with wrap_context('creating job resource'):
        save_deployment_phase(deployment.id, 'creating cluster resources')
        image_name = get_job_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag)

        logger.info(f'provisioning job {manifest.name} from image {image_name}')
        job_deployer = get_job_deployer(deployment.infrastructure_target)

        family = create_job_family_if_not_exist(manifest.name)
        family_dto = job_family_model_to_dto(family)

        all_build_vars = merge_env_vars(manifest.build_env, secret_build_env)
        all_runtime_vars = merge_env_vars(manifest.runtime_env, secret_runtime_env)
        runtime_env_vars = manifest.runtime_env or {}
        # Clear out unused build vars to hide secrets and avoid conflicts with env vars at runtime
        for build_var in all_build_vars.keys():
            if build_var not in all_runtime_vars:
                runtime_env_vars[build_var] = ''

        job_type: JobType = load_job_type(plugin_engine, manifest.get_jobtype())

        job: JobDto = safe_call(
            job_deployer.deploy_job,
            manifest=manifest,
            config=config,
            plugin_engine=plugin_engine,
            tag=tag,
            runtime_env_vars=runtime_env_vars,
            family=family_dto,
            containers_num=job_type.containers_num,
            runtime_secret_vars=secret_runtime_env,
        )

    with wrap_context('saving job in database'):
        job.deployed_by = deployment.deployed_by
        job.manifest = manifest
        job.manifest_yaml = deployment.manifest_yaml
        job.job_type_version = f'{job_type.lang_name}:{job_type.version}'
        save_job_model(job)

    with wrap_context('verifying deployed job'):
        save_deployment_phase(deployment.id, 'starting Job server')

        def on_job_alive():
            save_deployment_phase(deployment.id, 'initializing Job entrypoint')

        check_job_condition(job, on_job_alive)

    with wrap_context('invoking post-deploy actions'):
        save_deployment_phase(deployment.id, 'post-deploy hooks')
        post_job_deploy(manifest, job, image_name, deployment,
                        auth_subject, previous_job, plugin_engine)

    job.status = JobStatus.RUNNING.value
    update_job(job)

    metric_deployed_job.inc()
    logger.info(f'job {manifest.name} v{manifest.version} has been provisioned, deployment ID: {deployment.id}')
    return job


def post_job_deploy(
    manifest: Manifest,
    job: JobDto,
    image_name: str,
    deployment: DeploymentDto,
    auth_subject: models.AuthSubject | None,
    previous_job: JobDto | None,
    plugin_engine: PluginEngine,
):
    """Supplementary actions invoked after job is deployed"""
    plugin_engine.invoke_plugin_hook(PluginCore.post_job_deploy, manifest, job, image_name, deployer_username=deployment.deployed_by)

    if auth_subject is not None and previous_job is None:
        with wrap_context('granting permissions'):
            grant_permission(auth_subject, job.name, job.version, AuthScope.READ_JOB.value)
            grant_permission(auth_subject, job.name, job.version, AuthScope.CALL_JOB.value)
            grant_permission(auth_subject, job.name, job.version, AuthScope.DEPLOY_JOB.value)
            grant_permission(auth_subject, job.name, job.version, AuthScope.DELETE_JOB.value)

    with wrap_context('registering public endpoint requests'):
        if manifest.public_endpoints:
            for endpoint in manifest.public_endpoints:
                create_job_public_endpoint_if_not_exist(job.name, job.version, endpoint)

    if previous_job is None:
        AuditLogger().log_event(
            AuditLogEventType.JOB_DEPLOYED,
            username_executor=deployment.deployed_by,
            job_name=job.name,
            job_version=job.version,
        )
    else:
        AuditLogger().log_event(
            AuditLogEventType.JOB_REDEPLOYED,
            username_executor=deployment.deployed_by,
            username_subject=previous_job.deployed_by,
            job_name=job.name,
            job_version=job.version,
        )
