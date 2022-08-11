from typing import Optional

from lifecycle.config import Config
from lifecycle.deployer.deploy import build_and_provision, provision_fatman
from lifecycle.deployer.deployers import get_fatman_deployer
from lifecycle.deployer.secrets import FatmanSecrets
from lifecycle.fatman.deployment import create_deployment, save_deployment_result
from lifecycle.fatman.registry import read_fatman
from lifecycle.django.registry import models
from racetrack_client.log.context_error import wrap_context
from racetrack_client.manifest.manifest import Manifest
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.entities.dto import DeploymentStatus


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

    deployment_id = create_deployment(manifest, deployer_username)
    try:
        fatman_secrets = _retrieve_fatman_secrets(config, manifest, plugin_engine)

        with wrap_context('redeploying fatman'):
            build_and_provision(
                config, manifest, fatman_secrets, deployment_id,
                build_context=None,
                deployer_username=deployer_username,
                auth_subject=auth_subject,
                previous_fatman=fatman,
                plugin_engine=plugin_engine,
            )

        save_deployment_result(deployment_id, DeploymentStatus.DONE)

    except BaseException as e:
        save_deployment_result(deployment_id, DeploymentStatus.FAILED, error=str(e))
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

    deployment_id = create_deployment(manifest, deployer_username)
    try:
        if manifest.secret_runtime_env_file:
            fatman_secrets = _retrieve_fatman_secrets(config, manifest, plugin_engine)
        else:
            fatman_secrets = FatmanSecrets(git_credentials=None, secret_build_env={}, secret_runtime_env={})

        with wrap_context('reprovisioning fatman'):
            provision_fatman(
                config, manifest, fatman.image_tag, fatman_secrets.secret_build_env,
                fatman_secrets.secret_runtime_env, deployment_id, deployer_username,
                auth_subject, None, plugin_engine,
            )

        save_deployment_result(deployment_id, DeploymentStatus.DONE)

    except BaseException as e:
        save_deployment_result(deployment_id, DeploymentStatus.FAILED, error=str(e))
        raise e


def _retrieve_fatman_secrets(config: Config, manifest: Manifest, plugin_engine: PluginEngine) -> FatmanSecrets:
    with wrap_context('retrieving fatman secrets'):
        fatman_deployer = get_fatman_deployer(config, plugin_engine)
        return fatman_deployer.get_fatman_secrets(manifest.name, manifest.version)
