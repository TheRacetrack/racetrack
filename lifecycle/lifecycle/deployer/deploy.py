import logging
import threading
from typing import Optional

from racetrack_client.client.env import SecretVars
from racetrack_client.client_config.client_config import Credentials
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest import Manifest
from racetrack_client.utils.time import now
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.entities.dto import DeploymentStatus, FatmanDto
from lifecycle.config import Config
from lifecycle.deployer.builder import build_fatman, wait_for_image_builder_ready
from lifecycle.deployer.deployers import get_fatman_deployer
from lifecycle.deployer.permissions import check_deploy_permissions
from lifecycle.deployer.provision import provision_fatman
from lifecycle.deployer.secrets import FatmanSecrets
from lifecycle.django.registry import models
from lifecycle.fatman.deployment import create_deployment, save_deployment_result
from lifecycle.fatman.models_registry import fatman_exists, find_deleted_fatman

logger = get_logger(__name__)


def deploy_new_fatman(
    config: Config,
    manifest: Manifest,
    git_credentials: Optional[Credentials],
    secret_vars: SecretVars,
    deployment_id: str,
    build_context: Optional[str],
    force: bool,
    deployer_username: str,
    auth_subject: models.AuthSubject,
    plugin_engine: PluginEngine,
):
    """Deploy (build and provision) new Fatman instance, providing secrets"""
    _protect_fatman_overwriting(manifest, force)
    check_deploy_permissions(auth_subject, manifest)

    with wrap_context('saving fatman secrets'):
        fatman_secrets = FatmanSecrets(
            git_credentials=git_credentials,
            secret_build_env=secret_vars.build_env,
            secret_runtime_env=secret_vars.runtime_env,
        )
        fatman_deployer = get_fatman_deployer(config, plugin_engine)
        try:
            fatman_deployer.save_fatman_secrets(manifest.name, manifest.version, fatman_secrets)
        except NotImplementedError:
            logging.warning(f'managing secrets is not supported on {config.deployer}')

    build_and_provision(
        config, manifest, fatman_secrets, deployment_id, build_context,
        deployer_username, auth_subject, None, plugin_engine,
    )


def build_and_provision(
    config: Config,
    manifest: Manifest,
    fatman_secrets: FatmanSecrets,
    deployment_id: str,
    build_context: Optional[str],
    deployer_username: str,
    auth_subject: Optional[models.AuthSubject],
    previous_fatman: Optional[FatmanDto],
    plugin_engine: PluginEngine,
):
    """Build a Fatman image from a manifest file and provision it (deploy to a cluster)"""
    tag = now().strftime(r'%Y-%m-%dT%H%M%S')
    build_fatman(config, manifest, fatman_secrets, deployment_id, build_context, tag)
    provision_fatman(
        config, manifest, tag, fatman_secrets.secret_build_env,
        fatman_secrets.secret_runtime_env, deployment_id, deployer_username,
        auth_subject, previous_fatman, plugin_engine,
    )


def deploy_fatman_in_background(
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
    Schedule deployment of a fatman in background
    :return: deployment ID
    """
    deployment_id = create_deployment(manifest, username)
    logger.info(f'starting deployment {deployment_id} in background')
    args = (config, manifest, git_credentials, secret_vars, deployment_id,
            build_context, force, plugin_engine, username, auth_subject)
    thread = threading.Thread(target=deploy_fatman_saving_result, args=args, daemon=True)
    thread.start()
    return deployment_id


def deploy_fatman_saving_result(
    config: Config,
    manifest: Manifest,
    git_credentials: Optional[Credentials],
    secret_vars: SecretVars,
    deployment_id: str,
    build_context: Optional[str],
    force: bool,
    plugin_engine: PluginEngine,
    username: str,
    auth_subject: models.AuthSubject,
):
    """Deploy a Fatman storing its faulty or successful result in DB"""
    try:
        wait_for_image_builder_ready(config)
        deploy_new_fatman(
            config, manifest, git_credentials, secret_vars, deployment_id,
            build_context, force, username, auth_subject, plugin_engine,
        )
        save_deployment_result(deployment_id, DeploymentStatus.DONE)
    except BaseException as e:
        log_exception(e)
        save_deployment_result(deployment_id, DeploymentStatus.FAILED, error=str(e))


def _protect_fatman_overwriting(manifest: Manifest, force: bool):
    if fatman_exists(manifest.name, manifest.version):
        if force:
            logger.info(f'overwriting fatman {manifest.name} v{manifest.version} due to force deployment')
            return

        raise RuntimeError(f'fatman {manifest.name} v{manifest.version} is already deployed. '
                           'Try deploying next version or use --force flag')

    else:
        trash_fatman = find_deleted_fatman(manifest.name, manifest.version)
        if trash_fatman is not None:
            if force:
                logger.info(f'deploying fatman {manifest.name} v{manifest.version} again due to force deployment')
                return

            raise RuntimeError(f'Fatman {manifest.name} v{manifest.version} has already been deployed and deleted. '
                               f'Can\'t claim it again to prevent accidental/hostile reusing.')
