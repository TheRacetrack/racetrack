from typing import Dict, Optional

from lifecycle.auth.authorize import grant_permission
from lifecycle.config import Config
from lifecycle.deployer.deployers import get_fatman_deployer
from lifecycle.deployer.permissions import check_deploy_permissions
from lifecycle.django.registry import models
from lifecycle.fatman.audit import AuditLogger
from lifecycle.fatman.deployment import save_deployment_phase
from lifecycle.fatman.dto_converter import fatman_family_model_to_dto
from lifecycle.fatman.models_registry import create_fatman_family_if_not_exist, save_fatman_model
from lifecycle.fatman.public_endpoints import create_fatman_public_endpoint_if_not_exist
from lifecycle.monitor.monitors import check_fatman_condition
from lifecycle.server.metrics import metric_deployed_fatman
from racetrack_client.client.env import hide_env_vars, merge_env_vars
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest import Manifest
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.deploy.image import get_fatman_image
from racetrack_commons.entities.audit import AuditLogEventType
from racetrack_commons.entities.dto import FatmanDto

logger = get_logger(__name__)


def provision_fatman(
    config: Config,
    manifest: Manifest,
    tag: str,
    secret_build_env: Dict[str, str],
    secret_runtime_env: Dict[str, str],
    deployment_id: str,
    deployer_username: Optional[str],
    auth_subject: Optional[models.AuthSubject],
    previous_fatman: Optional[FatmanDto],
    plugin_engine: PluginEngine,
) -> FatmanDto:
    """
    Deploy built Fatman to a cluster
    :param previous_fatman: previous fatman version in case of redeploying
    """
    if auth_subject is not None:
        check_deploy_permissions(auth_subject, manifest)

    with wrap_context('creating fatman resource'):
        save_deployment_phase(deployment_id, 'creating cluster resources')
        image_name = get_fatman_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag)

        logger.info(f'provisioning fatman {manifest.name} from image {image_name}')
        fatman_deployer = get_fatman_deployer(config, plugin_engine)

        family = create_fatman_family_if_not_exist(manifest.name)
        family_dto = fatman_family_model_to_dto(family)

        runtime_env_vars = merge_env_vars(manifest.runtime_env, secret_runtime_env)
        build_env_vars = merge_env_vars(manifest.build_env, secret_build_env)
        runtime_env_vars = hide_env_vars(runtime_env_vars, build_env_vars)

        fatman = fatman_deployer.deploy_fatman(manifest, config, plugin_engine,
                                               tag, runtime_env_vars, family_dto)
        fatman.deployed_by = deployer_username

    with wrap_context('saving fatman in database'):
        save_fatman_model(fatman)

    with wrap_context('verifying deployed fatman'):
        save_deployment_phase(deployment_id, 'starting Fatman server')

        def on_fatman_alive():
            save_deployment_phase(deployment_id, 'initializing Fatman entrypoint')

        check_fatman_condition(fatman, config, on_fatman_alive, plugin_engine)

    with wrap_context('invoking post-deploy actions'):
        save_deployment_phase(deployment_id, 'post-deploy hooks')
        post_fatman_deploy(manifest, fatman, image_name, deployer_username,
                           auth_subject, previous_fatman, plugin_engine)

    metric_deployed_fatman.inc()
    logger.info(f'fatman {manifest.name} v{manifest.version} has been provisioned, deployment ID: {deployment_id}')
    return fatman


def post_fatman_deploy(
    manifest: Manifest,
    fatman: FatmanDto,
    image_name: str,
    deployer_username: Optional[str],
    auth_subject: Optional[models.AuthSubject],
    previous_fatman: Optional[FatmanDto],
    plugin_engine: PluginEngine,
):
    """Supplementary actions invoked after fatman is deployed"""
    plugin_engine.invoke_plugin_hook(PluginCore.post_fatman_deploy, manifest, fatman, image_name, deployer_username=deployer_username)

    if auth_subject is not None and previous_fatman is None:
        with wrap_context('granting permissions'):
            grant_permission(auth_subject, fatman.name, fatman.version, AuthScope.READ_FATMAN.value)
            grant_permission(auth_subject, fatman.name, fatman.version, AuthScope.CALL_FATMAN.value)
            grant_permission(auth_subject, fatman.name, fatman.version, AuthScope.DEPLOY_FATMAN.value)
            grant_permission(auth_subject, fatman.name, fatman.version, AuthScope.DELETE_FATMAN.value)

    with wrap_context('registering public endpoint requests'):
        if manifest.public_endpoints:
            for endpoint in manifest.public_endpoints:
                create_fatman_public_endpoint_if_not_exist(fatman.name, fatman.version, endpoint)

    if previous_fatman is None:
        AuditLogger().log_event(
            AuditLogEventType.FATMAN_DEPLOYED,
            username_executor=deployer_username,
            fatman_name=fatman.name,
            fatman_version=fatman.version,
        )
    else:
        AuditLogger().log_event(
            AuditLogEventType.FATMAN_REDEPLOYED,
            username_executor=deployer_username,
            username_subject=previous_fatman.deployed_by,
            fatman_name=fatman.name,
            fatman_version=fatman.version,
        )
