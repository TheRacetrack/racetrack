from __future__ import annotations
import os
from pathlib import Path
import time

import backoff

from image_builder.base import ImageBuilder
from image_builder.config import Config
from image_builder.docker.template import template_dockerfile
from racetrack_commons.deploy.job_type import JobType, load_job_type
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
from racetrack_commons.deploy.image import get_fatman_image
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
        env_vars: dict[str, str],
        deployment_id: str,
        plugin_engine: PluginEngine,
    ) -> tuple[list[str], str, str | None]:
        """Build image from manifest file in a workspace directory and return built image name"""
        job_type: JobType = load_job_type(plugin_engine, manifest.lang)

        _wait_for_docker_engine_ready()

        metric_labels = {
            'fatman_name': manifest.name,
            'fatman_version': manifest.version,
        }
        Path(config.build_logs_dir).mkdir(parents=True, exist_ok=True)
        logs_filename = f'{config.build_logs_dir}/{deployment_id}.log'

        logs: str = ''
        built_images: list[str] = []
        images_num = len(job_type.template_paths)
        for image_index in range(images_num):
            progress = f'({image_index+1}/{images_num})'

            with wrap_context(f'building base image {progress}'):
                base_image = _build_base_image(config, job_type, image_index, deployment_id, metric_labels)

            template_path = job_type.template_paths[image_index]
            if template_path is None:
                assert manifest.docker and manifest.docker.dockerfile_path, 'User-module Dockerfile manifest.docker.dockerfile_path is expected'
                dockerfile_path = workspace / manifest.docker.dockerfile_path
            else:
                with wrap_context(f'templating Dockerfile {progress}'):
                    dockerfile_path = workspace / f'.fatman-{image_index}.Dockerfile'
                    racetrack_version = os.environ.get('DOCKER_TAG', 'latest')
                    template_dockerfile(manifest, template_path, dockerfile_path, base_image,
                                        git_version, racetrack_version, job_type.version, env_vars)

            try:

                fatman_image = get_fatman_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag, image_index)
                logger.info(f'building Fatman image {progress}: {fatman_image}, deployment ID: {deployment_id}, keeping logs in {logs_filename}')
                with wrap_context(f'building fatman image {progress}'):
                    logs += build_container_image(fatman_image, dockerfile_path, workspace, metric_labels, logs_filename)
                    logger.info(f'Fatman image {progress} has been built: {fatman_image}')
                        
                built_images.append(fatman_image)
                metric_images_built.inc()
            except CommandError as e:
                metric_images_building_errors.inc()
                logger.error(f'building Fatman image {progress}: {e}')
                return built_images, e.stdout, f'building Fatman image {progress}: {e}'
            except Exception as e:
                metric_images_building_errors.inc()
                raise ContextError(f'building Fatman image {progress}') from e

        return built_images, logs, None


def _build_base_image(
    config: Config,
    job_type: JobType,
    image_index: int,
    deployment_id: str,
    metric_labels: dict[str, str],
) -> str:
    if job_type.base_image_paths[image_index] is None:
        return ''
        
    base_image = get_base_image_name(
        config.docker_registry, config.docker_registry_namespace,
        job_type.lang_name, job_type.version, image_index,
    )
    if not config.cache_base_images or not _image_exists_in_registry(base_image):
        base_logs_filename = f'{config.build_logs_dir}/{deployment_id}.base.log'
        logger.info(f'rebuilding base image {base_image}, '
                    f'deployment ID: {deployment_id}, keeping logs in {base_logs_filename}')
        build_container_image(
            base_image,
            job_type.base_image_paths[image_index],
            job_type.base_image_paths[image_index].parent,
            metric_labels,
            base_logs_filename,
        )
        logger.info(f'base Fatman image has been built and pushed: {base_image}')
    return base_image


def build_container_image(
    image_name: str,
    dockerfile_path: Path,
    context_dir: Path,
    metric_labels: dict[str, str],
    logs_filename: str | None = None,
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


def get_base_image_name(docker_registry: str, registry_namespace: str, name: str, tag: str, module_index: int = 0) -> str:
    """Return full name of Fatman entrypoint image"""
    if module_index == 0:
        image_type = 'fatman-base'
    else:
        image_type = f'fatman-base-{module_index}'
    return join_paths(docker_registry, registry_namespace, image_type, f'{name}:{tag}')
