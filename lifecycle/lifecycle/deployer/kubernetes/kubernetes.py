import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from base64 import b64decode, b64encode

from jinja2 import Template
from kubernetes import client
from kubernetes.client import ApiException
from kubernetes.config import load_incluster_config
from kubernetes.client import V1Secret

from lifecycle.auth.subject import get_auth_subject_by_fatman_family
from lifecycle.config import Config
from lifecycle.deployer.base import FatmanDeployer
from lifecycle.deployer.secrets import FatmanSecrets
from lifecycle.fatman.models_registry import read_fatman_family_model
from racetrack_client.client.env import merge_env_vars
from racetrack_client.client_config.client_config import Credentials
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest import Manifest
from racetrack_client.manifest.manifest import ResourcesManifest
from racetrack_client.utils.datamodel import convert_to_json, parse_dict_datamodel
from racetrack_client.utils.shell import shell
from racetrack_client.utils.time import datetime_to_timestamp, now
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.api.debug import debug_mode_enabled
from racetrack_commons.api.tracing import get_tracing_header_name
from racetrack_commons.deploy.image import get_fatman_image, get_fatman_user_module_image
from racetrack_commons.deploy.resource import fatman_resource_name, fatman_internal_name, \
    fatman_user_module_resource_name
from racetrack_commons.entities.dto import FatmanDto, FatmanStatus, FatmanFamilyDto

logger = get_logger(__name__)


class KubernetesFatmanDeployer(FatmanDeployer):
    def deploy_fatman(self,
                      manifest: Manifest,
                      config: Config,
                      plugin_engine: PluginEngine,
                      tag: str,
                      runtime_env_vars: Dict[str, str],
                      family: FatmanFamilyDto,
                      ) -> FatmanDto:
        """Deploy Job on Kubernetes and expose Service accessible by Fatman name"""
        resource_name = fatman_resource_name(manifest.name, manifest.version)
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

        plugin_vars_list = plugin_engine.invoke_plugin_hook(PluginCore.fatman_runtime_env_vars)
        for plugin_vars in plugin_vars_list:
            if plugin_vars:
                common_env_vars = merge_env_vars(common_env_vars, plugin_vars)

        conflicts = common_env_vars.keys() & runtime_env_vars.keys()
        if conflicts:
            raise RuntimeError(f'found illegal runtime env vars, which conflict with reserved names: {conflicts}')
        runtime_env_vars = merge_env_vars(runtime_env_vars, common_env_vars)

        resources = manifest.resources or ResourcesManifest()
        memory_min = resources.memory_min or config.default_fatman_memory_min
        memory_max = resources.memory_max or config.default_fatman_memory_max
        cpu_min = resources.cpu_min or config.default_fatman_cpu_min
        cpu_max = resources.cpu_max or config.default_fatman_cpu_max
        if memory_min.plain_number * 4 < memory_max.plain_number:
            memory_min = memory_max / 4
            logger.info(f'minimum memory increased to memory_max/4: {memory_min}')

        assert memory_max <= config.max_fatman_memory_limit, \
            f'given memory limit {memory_max} is greater than max allowed {config.max_fatman_memory_limit}'
        assert memory_min, 'memory_min must be greater than zero'
        assert cpu_min, 'cpu_min must be greater than zero'
        assert memory_min <= memory_max, 'memory_min must be less than memory_max'
        assert cpu_min <= cpu_max, 'cpu_min must be less than cpu_max'

        render_vars = {
            'resource_name': resource_name,
            'manifest': manifest,
            'entrypoint_image': get_fatman_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag),
            'deployment_timestamp': deployment_timestamp,
            'env_vars': runtime_env_vars,
            'user_module_image': None,
            'user_module_container': None,
            'memory_min': memory_min,
            'memory_max': memory_max,
            'cpu_min': cpu_min,
            'cpu_max': cpu_max,
            'fatman_k8s_namespace': os.environ.get('FATMAN_K8S_NAMESPACE', 'racetrack'),
        }
        if manifest.docker and manifest.docker.dockerfile_path:  # Dockerfile job type
            render_vars['user_module_image'] = get_fatman_user_module_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag)
            render_vars['user_module_container'] = fatman_user_module_resource_name(manifest.name, manifest.version)
            render_vars['env_vars']['FATMAN_ENTRYPOINT_HOSTNAME'] = 'localhost'

        _apply_templated_resource('fatman_template.yaml', render_vars)

        return FatmanDto(
            name=manifest.name,
            version=manifest.version,
            status=FatmanStatus.RUNNING.value,
            create_time=deployment_timestamp,
            update_time=deployment_timestamp,
            manifest=manifest,
            internal_name=fatman_internal_name(resource_name, '', config.deployer),
            image_tag=tag,
        )

    def delete_fatman(self, fatman_name: str, fatman_version: str):
        k8s_client = self._k8s_api_client()
        resource_name = fatman_resource_name(fatman_name, fatman_version)

        apps_api = client.AppsV1Api(k8s_client)
        apps_api.delete_namespaced_deployment(resource_name, namespace='racetrack')
        logger.info(f'deleted k8s deployment: {resource_name}')

        core_api = client.CoreV1Api(k8s_client)
        core_api.delete_namespaced_service(resource_name, namespace='racetrack')
        logger.info(f'deleted k8s service: {resource_name}')

        try:
            core_api.delete_namespaced_secret(resource_name, namespace='racetrack')
            logger.info(f'deleted k8s secret: {resource_name}')
        except ApiException as e:
            if e.reason == 'Not Found':
                logger.warning(f'k8s secret "{resource_name}" was not found')
            else:
                raise e

        try:
            custom_objects_api = client.CustomObjectsApi(k8s_client)
            custom_objects_api.delete_namespaced_custom_object('monitoring.coreos.com', 'v1', 'racetrack', 'servicemonitors',
                                                               resource_name)
            logger.info(f'deleted k8s servicemonitor: {resource_name}')
        except ApiException as e:
            if e.reason == 'Not Found':
                logger.warning(f'k8s servicemonitor "{resource_name}" was not found')
            else:
                raise e

    def fatman_exists(self, fatman_name: str, fatman_version: str) -> bool:
        k8s_client = self._k8s_api_client()
        apps_api = client.AppsV1Api(k8s_client)
        try:
            resource_name = fatman_resource_name(fatman_name, fatman_version)
            apps_api.read_namespaced_deployment(resource_name, namespace='racetrack')
            return True
        except ApiException as e:
            if e.reason == 'Not Found':
                return False
            raise e

    @staticmethod
    def _k8s_api_client() -> client.ApiClient:
        load_incluster_config()
        return client.ApiClient()

    def save_fatman_secrets(self,
                            fatman_name: str,
                            fatman_version: str,
                            fatman_secrets: FatmanSecrets,
                            ):
        """Create or update secrets needed to build and deploy a fatman"""
        resource_name = fatman_resource_name(fatman_name, fatman_version)
        render_vars = {
            'resource_name': resource_name,
            'fatman_name': fatman_name,
            'fatman_version': fatman_version,
            'git_credentials': _encode_secret_key(fatman_secrets.git_credentials),
            'secret_build_env': _encode_secret_key(fatman_secrets.secret_build_env),
            'secret_runtime_env': _encode_secret_key(fatman_secrets.secret_runtime_env),
            'fatman_k8s_namespace': os.environ.get('FATMAN_K8S_NAMESPACE', 'racetrack'),
        }
        _apply_templated_resource('secret_template.yaml', render_vars)

    def get_fatman_secrets(self,
                           fatman_name: str,
                           fatman_version: str,
                           ) -> FatmanSecrets:
        """Retrieve secrets for building and deploying a fatman"""
        k8s_client = self._k8s_api_client()
        core_api = client.CoreV1Api(k8s_client)

        resource_name = fatman_resource_name(fatman_name, fatman_version)
        try:
            secret: V1Secret = core_api.read_namespaced_secret(resource_name, namespace='racetrack')
        except ApiException as e:
            if e.reason == 'Not Found':
                raise RuntimeError(f"Can't find secrets associated with fatman {fatman_name} v{fatman_version}")
            else:
                raise e
        secret_data: Dict[str, str] = secret.data

        secret_build_env = _decode_secret_key(secret_data, 'secret_build_env') or {}
        secret_runtime_env = _decode_secret_key(secret_data, 'secret_runtime_env') or {}
        git_credentials_dict = _decode_secret_key(secret_data, 'git_credentials')
        git_credentials = parse_dict_datamodel(git_credentials_dict, Credentials) if git_credentials_dict else None

        return FatmanSecrets(
            git_credentials=git_credentials,
            secret_build_env=secret_build_env,
            secret_runtime_env=secret_runtime_env,
        )


def _apply_templated_resource(template_filename: str, render_vars: Dict[str, Any]):
    """Create resource from YAML template and apply it to kubernetes using kubectl apply"""
    fd, path = tempfile.mkstemp(prefix=template_filename, suffix='.yaml')
    try:
        resource_yaml = _template_resource(template_filename, render_vars)
        with open(fd, 'w') as f:
            f.write(resource_yaml)
        shell(f'kubectl apply -f {path}')
    finally:
        if not debug_mode_enabled():
            os.remove(path)


def _template_resource(template_filename: str, render_vars: Dict[str, Any]) -> str:
    """Load template from YAML, render templated vars and return as a string"""
    templates_dir = Path(__file__).parent.absolute()
    template_content = (templates_dir / template_filename).read_text()
    template = Template(template_content)
    templated = template.render(**render_vars)
    return templated


def _encode_secret_key(obj: Any) -> str:
    if obj is None:
        return ''
    obj_json: str = convert_to_json(obj)
    obj_encoded: str = b64encode(obj_json.encode()).decode()
    return obj_encoded


def _decode_secret_key(secret_data: Dict[str, str], key: str) -> Optional[Any]:
    encoded = secret_data.get(key)
    if not encoded:
        return None
    decoded_json: str = b64decode(encoded.encode()).decode()
    decoded_obj = json.loads(decoded_json)
    return decoded_obj
