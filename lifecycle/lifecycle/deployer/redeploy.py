from typing import Optional

from lifecycle.config import Config
from lifecycle.deployer.deploy import build_and_provision, provision_fatman
from lifecycle.deployer.deployers import get_fatman_deployer
from lifecycle.deployer.secrets import FatmanSecrets
from lifecycle.fatman.deployment import create_deployment, save_deployment_phase, save_deployment_result
from lifecycle.fatman.registry import decommission_fatman_infrastructure, read_fatman
from lifecycle.django.registry import models
from racetrack_client.log.context_error import wrap_context
from racetrack_client.manifest.manifest import Manifest
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.entities.dto import DeploymentStatus, FatmanDto


def redeploy_fatman(
    fatman_name: str,
    fatman_version: str,
    config: Config,
    plugin_engine: PluginEngine,
    deployer_username: str,
    auth_subject: Optional[models.AuthSubject],
):
    """Deploy (rebuild and reprovision) Fatman once again without knowing secrets"""
    fatman = read_fatman(fatman_name, fatman_version, config)
    manifest = fatman.manifest
    assert fatman.manifest is not None, "fatman doesn't have Manifest data specified"

    infra_target = fatman.infrastructure_target
    deployment = create_deployment(manifest, deployer_username, infra_target)
    try:
        fatman_secrets = _retrieve_fatman_secrets(config, manifest, plugin_engine, fatman)

        with wrap_context('redeploying fatman'):
            build_and_provision(
                config, manifest, fatman_secrets, deployment,
                build_context=None,
                auth_subject=auth_subject,
                previous_fatman=fatman,
                plugin_engine=plugin_engine,
            )

        save_deployment_result(deployment.id, DeploymentStatus.DONE)

    except BaseException as e:
        save_deployment_result(deployment.id, DeploymentStatus.FAILED, error=str(e))
        raise e


def reprovision_fatman(
    fatman_name: str,
    fatman_version: str,
    config: Config,
    plugin_engine: PluginEngine,
    deployer_username: str,
    auth_subject: Optional[models.AuthSubject],
):
    """Reprovision already built Fatman image once again to a cluster"""
    fatman = read_fatman(fatman_name, fatman_version, config)
    manifest = fatman.manifest
    assert fatman.manifest is not None, "fatman doesn't have Manifest data specified"
    assert fatman.image_tag is not None, "latest image tag is unknown"

    infra_target = fatman.infrastructure_target
    deployment = create_deployment(manifest, deployer_username, infra_target)
    try:
        if manifest.secret_runtime_env_file:
            fatman_secrets = _retrieve_fatman_secrets(config, manifest, plugin_engine, fatman)
        else:
            fatman_secrets = FatmanSecrets(git_credentials=None, secret_build_env={}, secret_runtime_env={})

        with wrap_context('reprovisioning fatman'):
            provision_fatman(
                config, manifest, fatman.image_tag, fatman_secrets.secret_build_env,
                fatman_secrets.secret_runtime_env, deployment,
                auth_subject, None, plugin_engine,
            )

        save_deployment_result(deployment.id, DeploymentStatus.DONE)

    except BaseException as e:
        save_deployment_result(deployment.id, DeploymentStatus.FAILED, error=str(e))
        raise e


def move_fatman(
    fatman_name: str,
    fatman_version: str,
    new_infra_target: str,
    config: Config,
    plugin_engine: PluginEngine,
    deployer_username: str,
    auth_subject: Optional[models.AuthSubject],
):
    """Move fatman from one infrastructure target to another"""
    fatman = read_fatman(fatman_name, fatman_version, config)
    manifest = fatman.manifest
    old_infra_target = fatman.infrastructure_target
    assert fatman.manifest is not None, "fatman doesn't have Manifest data specified"
    assert fatman.image_tag is not None, "fatman's image tag is unknown"
    assert new_infra_target, "infrastructure target has to be specified"
    assert new_infra_target != old_infra_target, "new infrastructure target has to be different from the current one"

    deployment = create_deployment(manifest, deployer_username, new_infra_target)
    try:
        if manifest.secret_runtime_env_file:
            fatman_secrets = _retrieve_fatman_secrets(config, manifest, plugin_engine, fatman)
        else:
            fatman_secrets = FatmanSecrets(git_credentials=None, secret_build_env={}, secret_runtime_env={})

        with wrap_context('deploying fatman to new infrastructure'):
            provision_fatman(
                config, manifest, fatman.image_tag, fatman_secrets.secret_build_env,
                fatman_secrets.secret_runtime_env, deployment,
                auth_subject, None, plugin_engine,
            )

        with wrap_context('deleting fatman from a former infrastructure'):
            save_deployment_phase(deployment.id, 'deleting fatman from a former infrastructure')
            decommission_fatman_infrastructure(
                fatman.name, fatman.version, old_infra_target, config, deployer_username, plugin_engine
            )

        save_deployment_result(deployment.id, DeploymentStatus.DONE)

    except BaseException as e:
        save_deployment_result(deployment.id, DeploymentStatus.FAILED, error=str(e))
        raise e


def _retrieve_fatman_secrets(config: Config, manifest: Manifest, plugin_engine: PluginEngine, fatman: FatmanDto) -> FatmanSecrets:
    with wrap_context('retrieving fatman secrets'):
        fatman_deployer = get_fatman_deployer(plugin_engine, fatman.infrastructure_target)
        return fatman_deployer.get_fatman_secrets(manifest.name, manifest.version)
