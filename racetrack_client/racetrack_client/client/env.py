from configparser import ConfigParser
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel

from racetrack_client.log.context_error import wrap_context
from racetrack_client.manifest import Manifest
from racetrack_client.utils.datamodel import parse_dict_datamodel
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class SecretVars(BaseModel):
    build_env: Dict[str, str] = {}
    runtime_env: Dict[str, str] = {}


def read_secret_vars(workdir: str, manifest: Manifest) -> SecretVars:
    secrets = SecretVars()
    secrets.build_env = read_secret_vars_from_file(workdir, manifest.secret_build_env_file, 'secret build vars')
    secrets.runtime_env = read_secret_vars_from_file(workdir, manifest.secret_runtime_env_file, 'secret runtime vars')
    return secrets


def read_secret_vars_from_file(workdir: str, secret_env_file: Optional[str], vars_name: str) -> Dict:
    if not secret_env_file:
        return {}

    secret_env_path = Path(workdir) / secret_env_file
    assert secret_env_path.is_file(), f"secret env file doesn't exist: {secret_env_path}"
    logger.info(f'reading {vars_name} from {secret_env_path}')
    return read_env_vars_from_file(secret_env_path)


def read_env_vars_from_file(path: Path) -> Dict[str, str]:
    with wrap_context('reading vars from env file'):
        config = ConfigParser()
        config.optionxform = str
        config.read_string("[config]\n" + path.read_text())
        env_dict = dict()
        for k, v in config["config"].items():
            env_dict[k] = v.strip('"').strip("'")
        return env_dict


def load_secret_vars_from_dict(secrets_dict: Optional[Dict[str, str]]) -> SecretVars:
    if secrets_dict is None:
        return SecretVars()
    with wrap_context('parsing secret_vars'):
        return parse_dict_datamodel(secrets_dict, SecretVars)


def merge_env_vars(env1: Optional[Dict[str, str]], env2: Optional[Dict[str, str]]) -> Dict[str, str]:
    if env1 is None:
        env1 = {}
    if env2 is None:
        env2 = {}
    return {**env1, **env2}


def hide_env_vars(runtime_env: Dict[str, str], build_env: Dict[str, str]) -> Dict[str, str]:
    """Shadow build vars in runtime env by adding empty values for them."""
    shadow = {k: '' for k, v in build_env.items()}
    return {**shadow, **runtime_env}
