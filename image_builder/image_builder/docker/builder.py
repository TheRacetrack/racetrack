from __future__ import annotations
import os
from pathlib import Path
import time

import backoff

from image_builder.base import ImageBuilder
from image_builder.config import Config
from image_builder.docker.template import template_dockerfile
from image_builder.progress import update_deployment_phase
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
from racetrack_commons.deploy.image import get_job_image
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
        """Build images from manifest file in a workspace directory and return built image name"""
        job_type: JobType = load_job_type(plugin_engine, manifest.lang)

        _wait_for_docker_engine_ready()

        metric_labels = {
            'job_name': manifest.name,
            'job_version': manifest.version,
        }
        Path(config.build_logs_dir).mkdir(parents=True, exist_ok=True)
        logs_filename = f'{config.build_logs_dir}/{deployment_id}.log'

        logs: list[str] = []
        built_images: list[str] = []
        images_num = len(job_type.template_paths)
        for image_index in range(images_num):
            progress = f'({image_index+1}/{images_num})'

            try:
                _build_job_image(
                    config, manifest, workspace, tag, git_version, env_vars, deployment_id, job_type,
                    metric_labels, image_index, images_num, logs_filename, logs, built_images,
                )
                metric_images_built.inc()

            except ContextError as e:
                metric_images_building_errors.inc()
                if isinstance(e.__cause__, CommandError):
                    logger.error(f'building Job image {progress}: {e}')
                    return built_images, e.__cause__.stdout, f'building Job image {progress}: {e}'
                raise ContextError(f'building Job image {progress}') from e
            except Exception as e:
                metric_images_building_errors.inc()
                raise ContextError(f'building Job image {progress}') from e

        return built_images, '\n'.join(logs), None


def _build_job_image(
    config: Config,
    manifest: Manifest,
    workspace: Path,
    tag: str,
    git_version: str,
    env_vars: dict[str, str],
    deployment_id: str,
    job_type: JobType,
    metric_labels: dict[str, str],
    image_index: int,
    images_num: int,
    logs_filename: str,
    logs: list[str],
    built_images: list[str],
):
    progress = f'({image_index+1}/{images_num})'
    build_progress = f'({image_index*2+1}/{images_num*2})'  # 2 actual builds (base + final) per job's image

    with wrap_context(f'building base image {progress}'):
        update_deployment_phase(config, deployment_id, f'building image {build_progress}')
        base_image = _build_base_image(
            config, job_type, image_index, deployment_id, metric_labels, build_progress,
        )

    build_progress = f'({image_index*2+2}/{images_num*2})'
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

    with wrap_context(f'building job image {progress}'):
        job_image = get_job_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag, image_index)
        logger.info(f'building Job image {progress}: {job_image}, deployment ID: {deployment_id}, keeping logs in {logs_filename}')
        update_deployment_phase(config, deployment_id, f'building image {build_progress}')
        build_logs = build_container_image(
            config, job_image, dockerfile_path, workspace, metric_labels,
            logs_filename, deployment_id, build_progress,
        )
        logs.append(build_logs)
        logger.info(f'Job image {progress} has been built: {job_image}')

    built_images.append(job_image)


def _build_base_image(
    config: Config,
    job_type: JobType,
    image_index: int,
    deployment_id: str,
    metric_labels: dict[str, str],
    build_progress: str,
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
            config,
            base_image,
            job_type.base_image_paths[image_index],
            job_type.base_image_paths[image_index].parent,
            metric_labels,
            base_logs_filename,
            deployment_id,
            build_progress,
        )
        logger.info(f'base Job image has been built and pushed: {base_image}')
    return base_image


def build_container_image(
    config: Config,
    image_name: str,
    dockerfile_path: Path,
    context_dir: Path,
    metric_labels: dict[str, str],
    logs_filename: str,
    deployment_id: str,
    build_progress: str,
) -> str:
    """Build OCI container image from Dockerfile and push it to registry. Return build logs output"""
    # Build with host network to propagate DNS settings (network is still isolated within an image-builder pod).
    logs = shell_output(
        f'DOCKER_BUILDKIT=1 docker build -t {image_name} -f {dockerfile_path} --network=host {context_dir}',
        print_stdout=False,
        output_filename=logs_filename,
    )

    update_deployment_phase(config, deployment_id, f'pushing image {build_progress}')
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
    """Return full name of Job entrypoint image"""
    if module_index == 0:
        image_type = 'job-base'
    else:
        image_type = f'job-base-{module_index}'
    return join_paths(docker_registry, registry_namespace, image_type, f'{name}:{tag}')
