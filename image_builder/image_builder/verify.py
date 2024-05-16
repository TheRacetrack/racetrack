from pathlib import Path
from typing import Any, Optional

import yaml

from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest.load import JOB_MANIFEST_FILENAME, FORMER_MANIFEST_FILENAME, \
    load_manifest_dict_from_yaml
from racetrack_client.manifest.merge import merge_dicts

logger = get_logger(__name__)


def verify_manifest_consistency(submitted_yaml: str, workspace: Path, repo_dir: Path):
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

    if submitted_dict != repo_dict:
        logger.info(f'Submitted job manifest:\n{_sort_dict_keys(submitted_dict)}')
        logger.info(f'Manifest file in Job repository:\n{_sort_dict_keys(repo_dict)}')
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


def _sort_dict_keys(d: dict | Any) -> dict:
    if not isinstance(d, dict):
        return d
    return {k: _sort_dict_keys(v) for k, v in sorted(d.items())}
