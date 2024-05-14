import io
import shutil
import tarfile
import time
from base64 import b64decode
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import yaml

from racetrack_client.client.env import merge_env_vars
from racetrack_client.client_config.client_config import Credentials
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest.merge import merge_dicts
from racetrack_client.manifest.load import Manifest, JOB_MANIFEST_FILENAME, FORMER_MANIFEST_FILENAME, \
    load_manifest_dict_from_yaml
from racetrack_commons.dir import project_root
from image_builder.base import ImageBuilder
from image_builder.config import Config
from image_builder.docker.builder import DockerBuilder
from image_builder.git import fetch_repository
from image_builder.metrics import (metric_active_building_tasks,
                                   metric_image_building_request_duration,
                                   metric_image_building_requests,
                                   metric_image_building_done_requests)
from image_builder.phase import phase_context
from image_builder.progress import update_deployment_phase
from racetrack_commons.plugin.engine import PluginEngine

"""Supported image builders for different platforms"""
image_builders: Dict[str, ImageBuilder] = {
    'docker': DockerBuilder(),
}

logger = get_logger(__name__)


def build_job_image(
    config: Config,
    manifest: Manifest,
    git_credentials: Optional[Credentials],
    secret_build_env: Dict[str, str],
    tag: str,
    build_context: Optional[str],
    deployment_id: str,
    plugin_engine: PluginEngine,
    build_flags: list[str],
) -> Tuple[List[str], str, Optional[str]]:
    """Build image from given manifest and return built image name"""
    metric_labels = {
        'job_name': manifest.name,
        'job_version': manifest.version,
    }
    metric_image_building_requests.labels(**metric_labels).inc()
    metric_active_building_tasks.inc()
    start_time = time.time()
    try:
        with phase_context('fetching the source code', metric_labels, deployment_id, config):
            logger.debug(f'preparing workspace for {manifest.name} {manifest.version}, deployment ID: {deployment_id}')

            assert manifest.image_type in image_builders, f'not supported image_type: {manifest.image_type}'
            image_builder = image_builders[manifest.image_type]

            workspaces_path = project_root() / 'workspaces'
            workspaces_path.mkdir(parents=True, exist_ok=True)
            assert workspaces_path.is_dir(), 'workspaces directory doesn\'t exist'

            workspace, repo_dir, git_version = prepare_workspace(workspaces_path, manifest, git_credentials, build_context, deployment_id)

            if config.verify_manifest_consistency:
                _verify_manifest_consistency(manifest.origin_yaml_, workspace, repo_dir)

            (workspace / 'job.yaml').write_text(manifest.origin_yaml_)

        logger.info(f'building image {manifest.name} from manifest in workspace {workspace}, '
                    f'deployment ID: {deployment_id}, git version: {git_version}')
        build_env_vars = merge_env_vars(manifest.build_env, secret_build_env)
        image_names, logs, error = image_builder.build(config, manifest, workspace, tag, git_version,
                                                       build_env_vars, deployment_id, plugin_engine, build_flags)

        if config.clean_up_workspaces:
            with phase_context('cleaning up the workspace', metric_labels, deployment_id, config):
                if repo_dir.exists():
                    shutil.rmtree(repo_dir)

        update_deployment_phase(config, deployment_id, 'finalizing the build')
        logger.info(f'finished building an image {manifest.name} {manifest.version}, deployment ID: {deployment_id}, '
                    f'logs size: {len(logs)} bytes, image names: {image_names}')
        return image_names, logs, error

    finally:
        metric_image_building_done_requests.labels(**metric_labels).inc()
        metric_image_building_request_duration.labels(**metric_labels).inc(time.time() - start_time)
        metric_active_building_tasks.dec()


def prepare_workspace(
        workspaces_path: Path,
        manifest: Manifest,
        git_credentials: Optional[Credentials],
        build_context: Optional[str],
        deployment_id: str,
) -> Tuple[Path, Path, str]:
    """
    Prepare workspace with source files from a git repository or extracted build context.
    Return project path and project version
    """
    repo_dir = workspaces_path / deployment_id

    if build_context:
        with wrap_context('extracting build context'):
            logger.debug('extracting build context')
            bytes_decoded = b64decode(build_context)
            tar_stream = io.BytesIO(bytes_decoded)
            with tarfile.open(fileobj=tar_stream, mode='r:gz') as tar:
                tar.extractall(path=repo_dir)
            return repo_dir, repo_dir, 'tar'

    with wrap_context('fetching job repo'):
        workspace, git_version = fetch_repository(repo_dir, manifest, git_credentials)
        return workspace, repo_dir, git_version


def _verify_manifest_consistency(submitted_yaml: str, workspace: Path, repo_dir: Path):
    repo_file = _find_workspace_manifest_file(workspace, repo_dir)
    if not repo_file:
        logger.warning("Can't find manifest file in a Job repository to verify it with submitted YAML")
        return
    repo_content = repo_file.read_text()

    with wrap_context('parsing YAML manifest'):
        repo_dict = yaml.safe_load(repo_content)
        submitted_dict = yaml.safe_load(submitted_yaml)

    # take into account manifest extended by a base one
    extends = repo_dict.get('extends')
    if extends:
        base_path = repo_file.parent / Path(extends)
        with wrap_context('extending base manifest with overlay'):
            with wrap_context('loading base manifest'):
                base_manifest_dict = load_manifest_dict_from_yaml(base_path)
            with wrap_context('merging base & overlay layers'):
                repo_dict = merge_dicts(base_manifest_dict, repo_dict)
                repo_dict['extends'] = None

    if repo_dict != submitted_dict:
        raise RuntimeError('Submitted job manifest is not consistent with the file found in a repository. Did you forget to "git push"?')


def _find_workspace_manifest_file(workspace: Path, repo_dir: Path) -> Optional[Path]:
    paths_to_check = [
        workspace / JOB_MANIFEST_FILENAME,
        workspace / FORMER_MANIFEST_FILENAME,
        repo_dir / JOB_MANIFEST_FILENAME,
        repo_dir / FORMER_MANIFEST_FILENAME,
    ]
    for path in paths_to_check:
        if path.is_file():
            return path
    return None
