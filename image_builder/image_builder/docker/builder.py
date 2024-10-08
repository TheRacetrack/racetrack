import os
from pathlib import Path

import backoff

from image_builder.base import ImageBuilder
from image_builder.config import Config
from image_builder.docker.template import template_dockerfile
from image_builder.validate import validate_jobtype_manifest
from image_builder.metrics import (
    metric_images_built,
    metric_images_building_errors,
)
from image_builder.phase import phase_context
from racetrack_client.log.context_error import wrap_context, ContextError
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest import Manifest
from racetrack_client.utils.shell import shell, CommandError, shell_output
from racetrack_client.utils.url import join_paths
from racetrack_commons.deploy.image import get_job_image
from racetrack_commons.deploy.job_type import JobType, load_job_type, JobTypeImageDef, ImageSourceLocation
from racetrack_commons.plugin.engine import PluginEngine

logger = get_logger(__name__)
JOBTYPE_BUILD_CONTEXT = 'jobtype'


class DockerBuilder(ImageBuilder):
    def build(
        self,
        config: Config,
        manifest: Manifest,
        workspace: Path,
        tag: str,
        git_version: str,
        env_vars: dict[str, str],
        secret_env_vars: dict[str, str],
        deployment_id: str,
        plugin_engine: PluginEngine,
        build_flags: list[str],
    ) -> tuple[list[str], str, str | None]:
        """Build images from manifest file in a workspace directory and return built image name"""
        metric_labels = {
            'job_name': manifest.name,
            'job_version': manifest.version,
        }
        with phase_context('preparing job type builder', metric_labels, deployment_id, config):
            _wait_for_docker_engine_ready()

            job_type: JobType = load_job_type(plugin_engine, manifest.get_jobtype())
            validate_jobtype_manifest(job_type, manifest, plugin_engine)

            Path(config.build_logs_dir).mkdir(parents=True, exist_ok=True)
            logs_filename = f'{config.build_logs_dir}/{deployment_id}.log'

        logs: list[str] = []
        built_images: list[str] = []
        images_num = job_type.images_num
        for image_index in range(images_num):
            progress = f'({image_index+1}/{images_num})'

            try:
                _build_job_image(
                    config, manifest, workspace, tag, git_version, env_vars, secret_env_vars, deployment_id, job_type,
                    metric_labels, image_index, images_num, logs_filename, logs, built_images, build_flags
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
    job_workspace: Path,
    tag: str,
    git_version: str,
    env_vars: dict[str, str],
    secret_env_vars: dict[str, str],
    deployment_id: str,
    job_type: JobType,
    metric_labels: dict[str, str],
    image_index: int,
    images_num: int,
    logs_filename: str,
    logs: list[str],
    built_images: list[str],
    build_flags: list[str],
):
    progress = f'({image_index+1}/{images_num})'
    image_def: JobTypeImageDef = job_type.images[image_index]
    with phase_context(f'building image {progress}', metric_labels, deployment_id, config, metric_phase='building image'):

        base_image: str = ''  # Base images are deprecated, to be removed
        if image_def.base_image_path is not None:
            logger.warning('Using deprecated base images. Please use a single job template instead.')
            with wrap_context(f'building base image {progress}'):
                base_image = _build_base_image(config, job_type, image_def, image_index, deployment_id)

        src_dockerfile_path: Path = image_def.dockerfile_path
        if image_def.source == ImageSourceLocation.job:  # User-module Dockerfile from a Job's workspace
            src_dockerfile_path = job_workspace / image_def.dockerfile_path
            assert src_dockerfile_path.is_file(), f'User-module Dockerfile was not found in a job workspace: {image_def.dockerfile_path}'
        else:
            assert src_dockerfile_path.is_file(), f'Dockerfile was not found in a job type: {image_def.dockerfile_path}'

        dst_dockerfile_path: Path = src_dockerfile_path
        if image_def.template:
            with wrap_context(f'templating Dockerfile {progress}'):
                template_path: Path = src_dockerfile_path
                assert template_path.is_file(), f'Job template Dockerfile was not found: {template_path}'
                dst_dockerfile_path = job_workspace / f'.job-{image_index}.Dockerfile'
                racetrack_version = os.environ.get('DOCKER_TAG', 'latest')
                template_dockerfile(manifest, template_path, dst_dockerfile_path,
                                    git_version, racetrack_version, job_type.version, env_vars, base_image)

        image_name = get_job_image(config.docker_registry, config.docker_registry_namespace, manifest.name, tag, image_index)
        logger.info(f'building Job image {progress}: {image_name}, deployment ID: {deployment_id}, keeping logs in {logs_filename}')
        build_logs = _build_container_image(
            image_name, dst_dockerfile_path, job_workspace, job_type.jobtype_dir, logs_filename, build_flags, secret_env_vars,
        )
        logs.append(build_logs)

    with phase_context(f'pushing image {progress}', metric_labels, deployment_id, config, metric_phase='pushing image'):
        _push_container_image(image_name, logs_filename)
        logger.info(f'Job image {progress} has been built and pushed: {image_name}')

    built_images.append(image_name)


def _build_container_image(
    image_name: str,
    dockerfile_path: Path,
    job_workspace: Path,
    jobtype_dir: Path,
    logs_filename: str,
    build_flags: list[str],
    secret_env_vars: dict[str, str],
) -> str:
    """Build OCI container image from Dockerfile and push it to registry. Return build logs output"""
    # Build with host network to propagate DNS settings (network is still isolated within an image-builder pod).
    # Job workspace is the default build context

    # Ensure bad flags did not sneak in
    approved_flags = ['--no-cache']
    for flag in build_flags:
        if flag not in approved_flags:
            raise ValueError(f"Flag '{flag}' is not approved for use.")

    cmd_parts = [
        'DOCKER_BUILDKIT=1 docker buildx build',
        f'-t {image_name}',
        f'-f {dockerfile_path}',
        f'--network=host',
        f'--build-context {JOBTYPE_BUILD_CONTEXT}="{jobtype_dir}"',
    ]
    cmd_parts.extend(build_flags)

    build_secrets_path = job_workspace / 'build_secrets.env'
    if secret_env_vars:
        secrets_txt = '\n'.join(f'{key}="{value}"' for key, value in secret_env_vars.items())
        build_secrets_path.write_text(secrets_txt)
        cmd_parts.append(f'--secret id=build_secrets,src={build_secrets_path.absolute()}')
    else:
        build_secrets_path.write_text('')

    cmd_parts.append(str(job_workspace))

    try:
        logs = shell_output(
            ' '.join(cmd_parts),
            print_stdout=False,
            output_filename=logs_filename,
        )
    finally:
        if build_secrets_path:
            build_secrets_path.unlink()
    return logs


def _push_container_image(image_name: str, logs_filename: str) -> None:
    shell(f'docker push {image_name}', print_stdout=False, output_filename=logs_filename)


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
    shell('docker ps', print_stdout=False, print_log=False)


def get_base_image_name(docker_registry: str, registry_namespace: str, name: str, tag: str, module_index: int = 0) -> str:
    """Return full name of Job entrypoint image"""
    if module_index == 0:
        image_type = 'job-base'
    else:
        image_type = f'job-base-{module_index}'
    return join_paths(docker_registry, registry_namespace, image_type, f'{name}:{tag}')


def _build_base_image(
    config: Config,
    job_type: JobType,
    image_def: JobTypeImageDef,
    image_index: int,
    deployment_id: str,
) -> str:
    image_name = get_base_image_name(
        config.docker_registry, config.docker_registry_namespace,
        job_type.lang_name, job_type.version, image_index,
    )
    if config.cache_base_images and _image_exists_in_registry(image_name):
        return image_name

    logs_filename = f'{config.build_logs_dir}/{deployment_id}.base.log'
    logger.info(f'rebuilding base image {image_name}, '
                f'deployment ID: {deployment_id}, keeping logs in {logs_filename}')

    dockerfile_path = image_def.base_image_path
    assert dockerfile_path.is_file(), f'base Dockerfile doesn\'t exist: {dockerfile_path}'
    context_dir = dockerfile_path.parent
    shell_output(
        f'DOCKER_BUILDKIT=1 docker build -t {image_name} -f {dockerfile_path} --network=host '
        f'{context_dir}',
        print_stdout=False,
        output_filename=logs_filename,
    )

    shell(f'docker push {image_name}', print_stdout=False, output_filename=logs_filename)

    logger.info(f'base Job image has been built and pushed: {image_name}')
    return image_name
