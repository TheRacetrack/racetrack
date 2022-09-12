import re
from typing import Dict

from lifecycle.auth.subject import get_auth_subject_by_fatman_family
from lifecycle.config import Config
from lifecycle.deployer.base import FatmanDeployer
from lifecycle.deployer.secrets import FatmanSecrets
from lifecycle.fatman.models_registry import read_fatman_family_model
from racetrack_client.client.env import merge_env_vars
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest import Manifest
from racetrack_client.utils.shell import shell, shell_output
from racetrack_client.utils.time import datetime_to_timestamp, now
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.api.tracing import get_tracing_header_name
from racetrack_commons.deploy.image import get_fatman_image, get_fatman_user_module_image
from racetrack_commons.deploy.resource import fatman_resource_name, fatman_internal_name, FATMAN_INTERNAL_PORT, \
    fatman_user_module_resource_name
from racetrack_commons.entities.dto import FatmanDto, FatmanStatus, FatmanFamilyDto

logger = get_logger(__name__)


class DockerFatmanDeployer(FatmanDeployer):
    """FatmanDeployer managing workloads on a local docker instance, used mostly for testing purposes"""

    def deploy_fatman(self,
                      manifest: Manifest,
                      config: Config,
                      plugin_engine: PluginEngine,
                      tag: str,
                      runtime_env_vars: Dict[str, str],
                      family: FatmanFamilyDto,
                      ) -> FatmanDto:
        """Run Fatman as docker container on local docker"""
        if self.fatman_exists(manifest.name, manifest.version):
            self.delete_fatman(manifest.name, manifest.version)

        fatman_port = self._get_next_fatman_port()
        entrypoint_image_name = get_fatman_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag)
        entrypoint_resource_name = fatman_resource_name(manifest.name, manifest.version)
        deployment_timestamp = datetime_to_timestamp(now())
        family_model = read_fatman_family_model(family.name)
        auth_subject = get_auth_subject_by_fatman_family(family_model)

        common_env_vars = {
            'PUB_URL': config.internal_pub_url,
            'FATMAN_NAME': manifest.name,
            'AUTH_TOKEN': auth_subject.token,
            'FATMAN_DEPLOYMENT_TIMESTAMP': deployment_timestamp,
            'REQUEST_TRACING_HEADER': get_tracing_header_name(),
        }
        if config.open_telemetry_enabled:
            common_env_vars['OPENTELEMETRY_ENDPOINT'] = config.open_telemetry_endpoint

        conflicts = common_env_vars.keys() & runtime_env_vars.keys()
        if conflicts:
            raise RuntimeError(f'found illegal runtime env vars, which conflict with reserved names: {conflicts}')
        runtime_env_vars = merge_env_vars(runtime_env_vars, common_env_vars)
        plugin_vars_list = plugin_engine.invoke_plugin_hook(PluginCore.fatman_runtime_env_vars)
        for plugin_vars in plugin_vars_list:
            if plugin_vars:
                runtime_env_vars = merge_env_vars(runtime_env_vars, plugin_vars)
        env_vars_cmd = ' '.join([f'--env {env_name}="{env_val}"' for env_name, env_val in runtime_env_vars.items()])

        if manifest.docker and manifest.docker.dockerfile_path:
            user_module_resource_name = fatman_user_module_resource_name(manifest.name, manifest.version)
            user_module_port = fatman_port + 4  # in order not to conflict with other fatmen or Racetrack services
            user_module_image = get_fatman_user_module_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag)
            shell(
                f'docker run -d'
                f' --name {user_module_resource_name}'
                f' -p {user_module_port}:7004'
                f' {env_vars_cmd}'
                f' --pull always'
                f' --network="racetrack_default"'
                f' --add-host=host.docker.internal:host-gateway'
                f' {user_module_image}'
            )

        shell(
            f'docker run -d'
            f' --name {entrypoint_resource_name}'
            f' -p {fatman_port}:{FATMAN_INTERNAL_PORT}'
            f' {env_vars_cmd}'
            f' --pull always'
            f' --network="racetrack_default"'
            f' --add-host=host.docker.internal:host-gateway'
            f' --label fatman-name={manifest.name}'
            f' --label fatman-version={manifest.version}'
            f' {entrypoint_image_name}'
        )

        return FatmanDto(
            name=manifest.name,
            version=manifest.version,
            status=FatmanStatus.RUNNING.value,
            create_time=deployment_timestamp,
            update_time=deployment_timestamp,
            manifest=manifest,
            internal_name=fatman_internal_name(entrypoint_resource_name, str(fatman_port), config.deployer),
            image_tag=tag,
        )

    def delete_fatman(self, fatman_name: str, fatman_version: str):
        base_resource_name = fatman_resource_name(fatman_name, fatman_version)
        self._delete_container_if_exists(base_resource_name)
        user_module = fatman_user_module_resource_name(fatman_name, fatman_version)
        self._delete_container_if_exists(user_module)
        self._delete_container_if_exists(f'{base_resource_name}-entrypoint')

    def fatman_exists(self, fatman_name: str, fatman_version: str) -> bool:
        resource_name = fatman_resource_name(fatman_name, fatman_version)
        return self._container_exists(resource_name)

    @staticmethod
    def _container_exists(container_name: str) -> bool:
        output = shell_output(f'docker ps -a --filter "name=^/{container_name}$" --format "{{{{.Names}}}}"')
        return container_name in output.splitlines()

    def _delete_container_if_exists(self, container_name: str):
        if self._container_exists(container_name):
            shell(f'docker rm -f {container_name}')

    @staticmethod
    def _get_next_fatman_port() -> int:
        """Return next unoccupied port for Fatman"""
        output = shell_output('docker ps --filter "name=^/fatman-" --format "{{.Names}} {{.Ports}}"')
        occupied_ports = set()
        for line in output.splitlines():
            match = re.fullmatch(r'fatman-(.+) .+:(\d+)->.*', line.strip())
            if match:
                occupied_ports.add(int(match.group(2)))
        for port in range(7000, 8000, 10):
            if port not in occupied_ports:
                return port
        return 8000

    def save_fatman_secrets(self,
                            fatman_name: str,
                            fatman_version: str,
                            fatman_secrets: FatmanSecrets,
                            ):
        raise NotImplementedError("managing secrets is not supported on local docker")

    def get_fatman_secrets(self,
                           fatman_name: str,
                           fatman_version: str,
                           ) -> FatmanSecrets:
        raise NotImplementedError("managing secrets is not supported on local docker")
