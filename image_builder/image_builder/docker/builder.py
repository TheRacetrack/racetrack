import os
from pathlib import Path
import time
from typing import Optional, Dict, Tuple

import backoff

from image_builder.base import ImageBuilder
from image_builder.config import Config
from racetrack_commons.dir import project_root
from image_builder.docker.template import template_dockerfile
from image_builder.metrics import (
    metric_images_built,
    metric_images_building_errors,
    metric_images_pushed,
    metric_images_pushed_duration,
)
from racetrack_client.log.context_error import wrap_context, ContextError
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest import Manifest
from racetrack_client.utils.shell import shell, CommandError, shell_output
from racetrack_client.utils.url import join_paths
from racetrack_commons.deploy.image import get_fatman_base_image, get_fatman_image, get_fatman_user_module_image
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine

logger = get_logger(__name__)


class DockerBuilder(ImageBuilder):
    def build(
            self,
            config: Config,
            manifest: Manifest,
            workspace: Path,
            tag: str,
            git_version: str,
            env_vars: Dict[str, str],
            deployment_id: str,
            plugin_engine: PluginEngine,
    ) -> Tuple[str, str, Optional[str]]:
        """Build image from manifest file in a workspace directory and return built image name"""
        job_templates = _gather_job_templates(config, plugin_engine)
        assert job_templates, f'language {manifest.lang} is not supported, extend Racetrack with job type plugins'
        assert manifest.lang in job_templates, f'language {manifest.lang} is not supported, supported are: {list(job_templates.keys())}'

        base_image, template_path = job_templates[manifest.lang]

        _wait_for_docker_engine_ready()

        dockerfile_path = workspace / '.fatman.Dockerfile'
        with wrap_context('templating Dockerfile'):
            racetrack_version = os.environ.get('DOCKER_TAG', 'latest')
            template_dockerfile(manifest, template_path, dockerfile_path, base_image,
                                git_version, racetrack_version, env_vars)

        full_image = get_fatman_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag)
        metric_labels = {
            'fatman_name': manifest.name,
            'fatman_version': manifest.version,
        }
        Path(config.build_logs_dir).mkdir(parents=True, exist_ok=True)
        logs_filename = f'{config.build_logs_dir}/{deployment_id}.log'

        try:
            logger.info(f'building Fatman image: {full_image}, deployment ID: {deployment_id}, keeping logs in {logs_filename}')
            logs = build_container_image(full_image, dockerfile_path, workspace, metric_labels, logs_filename)
            logger.info(f'Fatman image has been built: {full_image}')

            if manifest.docker and manifest.docker.dockerfile_path:
                user_module_image = get_fatman_user_module_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag)
                logger.info(f'building Dockerfile-originated user-module image: {user_module_image}')
                dockerfile_path = workspace / manifest.docker.dockerfile_path
                logs = build_container_image(user_module_image, dockerfile_path, workspace, metric_labels, logs_filename)
                logger.info(f'finished building Dockerfile-originated user-module image: {user_module_image}')
            metric_images_built.inc()
        except CommandError as e:
            metric_images_building_errors.inc()
            logger.error(f'building Fatman image: {e}')
            return full_image, e.stdout, f'building Fatman image: {e}'
        except Exception as e:
            metric_images_building_errors.inc()
            raise ContextError('building Fatman image') from e

        return full_image, logs, None


def build_container_image(
    image_name: str,
    dockerfile_path: Path,
    context_dir: Path,
    metric_labels: Dict[str, str] = None,
    logs_filename: Optional[str] = None,
) -> str:
    """Build OCI container image from Dockerfile and push it to registry. Return build logs output"""
    # Build with host network to propagate DNS settings (network is still isolated within an image-builder pod).
    logs = shell_output(
        f'DOCKER_BUILDKIT=1 docker build -t {image_name} -f {dockerfile_path} --network=host {context_dir}',
        print_stdout=False,
        output_filename=logs_filename,
    )

    push_start_time = time.time()
    metric_labels = metric_labels or {}

    shell(f'docker push {image_name}', print_stdout=False, output_filename=logs_filename)

    metric_images_pushed.labels(**metric_labels).inc()
    metric_images_pushed_duration.labels(**metric_labels).inc(time.time() - push_start_time)

    return logs


@backoff.on_exception(backoff.fibo, CommandError, max_value=3, max_time=30, jitter=None)
def _wait_for_docker_engine_ready():
    shell('docker ps')


def _gather_job_templates(
    config: Config,
    plugin_engine: PluginEngine,
) -> Dict[str, Tuple[str, Path]]:
    """Return job name -> (base image name, dockerfile template path)"""
    job_templates: Dict[str, Tuple[str, Path]] = {}

    # job types from plugins
    docker_registry_prefix = join_paths(config.docker_registry, config.docker_registry_namespace, 'fatman-base')
    plugin_results = plugin_engine.invoke_plugin_hook(PluginCore.fatman_job_types, docker_registry_prefix)
    for plugin_job_types in plugin_results:
        for job_name, job_data in plugin_job_types.items():
            base_image, template_path = job_data
            assert template_path.is_file(), f'cannot find Dockerfile template for {job_name} language wrapper: {template_path}'
            job_templates[job_name] = (base_image, template_path)

    return job_templates
