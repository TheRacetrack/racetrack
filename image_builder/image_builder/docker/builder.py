import os
from pathlib import Path
import time
from typing import Optional, Dict, Tuple

import backoff

from image_builder.base import ImageBuilder
from image_builder.config import Config
from image_builder.docker.template import template_dockerfile
from image_builder.job_type import JobType, load_job_type
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
from racetrack_commons.deploy.image import get_fatman_image, get_fatman_user_module_image
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
        job_type: JobType = load_job_type(plugin_engine, manifest.lang)

        _wait_for_docker_engine_ready()

        metric_labels = {
            'fatman_name': manifest.name,
            'fatman_version': manifest.version,
        }
        Path(config.build_logs_dir).mkdir(parents=True, exist_ok=True)
        logs_filename = f'{config.build_logs_dir}/{deployment_id}.log'

        base_image = _build_base_image(config, job_type, deployment_id, metric_labels)

        with wrap_context('templating Dockerfile'):
            dockerfile_path = workspace / '.fatman.Dockerfile'
            racetrack_version = os.environ.get('DOCKER_TAG', 'latest')
            template_dockerfile(manifest, job_type.template_path, dockerfile_path, base_image,
                                git_version, racetrack_version, env_vars)

        full_image = get_fatman_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag)

        try:
            logger.info(f'building Fatman image: {full_image}, deployment ID: {deployment_id}, keeping logs in {logs_filename}')
            with wrap_context('building fatman image'):
                logs = build_container_image(full_image, dockerfile_path, workspace, metric_labels, logs_filename)
                logger.info(f'Fatman image has been built: {full_image}')

            if manifest.docker and manifest.docker.dockerfile_path:
                with wrap_context('building Dockerfile-originated user-module image'):
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


def _build_base_image(
    config: Config,
    job_type: JobType,
    deployment_id: str,
    metric_labels: Dict[str, str],
) -> str:
    base_image = join_paths(config.docker_registry, config.docker_registry_namespace, 'fatman-base', f'{job_type.lang_name}:{job_type.version}')
    if not _image_exists_in_registry(base_image):
        with wrap_context('building base image'):
            base_logs_filename = f'{config.build_logs_dir}/{deployment_id}.base.log'
            logger.info(f'base image not found in a registry, rebuilding {base_image}, '
                        f'deployment ID: {deployment_id}, keeping logs in {base_logs_filename}')
            build_container_image(
                base_image,
                job_type.base_image_path,
                job_type.base_image_path.parent,
                metric_labels,
                base_logs_filename,
            )
            logger.info(f'base Fatman image has been built and pushed: {base_image}')
    return base_image


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

    shell(f'docker push {image_name}', print_stdout=False, output_filename=logs_filename)

    if metric_labels:
        metric_images_pushed.labels(**metric_labels).inc()
        metric_images_pushed_duration.labels(**metric_labels).inc(time.time() - push_start_time)

    return logs


def _image_exists_in_registry(image_name: str):
    """
    Check if an image (with tag) exists in a remote Docker registry (local, private or public)
    This command is experimental feature in docker.
    """
    with wrap_context('checking if image exists in registry'):
        try:
            shell(f'docker manifest inspect --insecure {image_name}', print_stdout=False)
            return True
        except CommandError as e:
            if e.returncode == 1 and ("manifest unknown" in e.stdout or "no such manifest" in e.stdout):
                return False
            raise e


@backoff.on_exception(backoff.fibo, CommandError, max_value=3, max_time=30, jitter=None)
def _wait_for_docker_engine_ready():
    shell('docker ps')
