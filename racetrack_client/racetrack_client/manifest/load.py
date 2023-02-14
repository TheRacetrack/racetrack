from pathlib import Path
from typing import Dict, Optional

import yaml
from racetrack_client.log.context_error import wrap_context
from racetrack_client.manifest.manifest import Manifest
from racetrack_client.utils.datamodel import parse_dict_datamodel, parse_yaml_datamodel
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)

JOB_MANIFEST_FILENAME = 'job.yaml'
FORMER_MANIFEST_FILENAME = 'fatman.yaml'

def load_manifest_from_yaml(path: Path) -> Manifest:
    """Load Manifest from a YAML file. Data types validation happens here when parsing YAML."""
    manifest_dict = load_manifest_dict_from_yaml(path)
    return load_manifest_from_dict(manifest_dict)


def load_manifest_dict_from_yaml(path: Path) -> Dict:
    if not path.is_file():
        raise FileNotFoundError(f"local manifest file '{path}' doesn't exist")

    with wrap_context('loading YAML'):
        with path.open() as file:
            return yaml.load(file, Loader=yaml.FullLoader)


def load_manifest_from_dict(manifest_dict: Dict) -> Manifest:
    """Return manifest as data class"""
    with wrap_context('parsing manifest data types'):
        return parse_dict_datamodel(manifest_dict, Manifest)


def parse_manifest_or_empty(manifest_yaml: Optional[str]) -> Optional[Manifest]:
    """Parse YAML string as Manifest. In case of error return None"""
    if not manifest_yaml:
        return None
    try:
        return parse_yaml_datamodel(manifest_yaml, Manifest)
    except Exception as e:
        logger.error(f'Job Manifest YAML contains syntax error: {e}')
        return None


def get_manifest_path(workdir_or_file: str) -> Path:
    if Path(workdir_or_file).is_dir():
        manifest_path = Path(workdir_or_file) / JOB_MANIFEST_FILENAME
        if manifest_path.is_file():
            return manifest_path
        
        former_path = Path(workdir_or_file) / FORMER_MANIFEST_FILENAME
        if former_path.is_file():
            logger.warning(f'You are using old manifest file name "{FORMER_MANIFEST_FILENAME}". Please rename it to "{JOB_MANIFEST_FILENAME}"')
            return former_path
        
        raise FileNotFoundError(f"local manifest file '{manifest_path}' doesn't exist")

    else:
        manifest_path = Path(workdir_or_file)
        if not manifest_path.is_file():
            raise FileNotFoundError(f"local manifest file '{manifest_path}' doesn't exist")

        if manifest_path.name == FORMER_MANIFEST_FILENAME:
            logger.warning(f'You are using old manifest file name "{FORMER_MANIFEST_FILENAME}". Please rename it to "{JOB_MANIFEST_FILENAME}"')
            
        return manifest_path
