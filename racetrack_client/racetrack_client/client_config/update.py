from typing import Dict

from racetrack_client.log.context_error import wrap_context
from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.io import load_client_config, save_client_config
from racetrack_client.client_config.client_config import Credentials, ClientConfig
from racetrack_client.utils.url import trim_url
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def set_credentials(repo_url: str, username: str, token_password: str):
    client_config = load_client_config()
    repo_url = trim_url(repo_url)
    client_config.git_credentials[repo_url] = Credentials(username=username, password=token_password)
    logger.info(f'git credentials added for repo: {repo_url}')
    save_client_config(client_config)


def set_current_remote(remote: str):
    set_config_setting('lifecycle_url', remote)
    logger.info(f'Current remote set to "{remote}"')


def get_current_remote():
    client_config = load_client_config()
    remote_name = client_config.lifecycle_url
    remote_url = resolve_lifecycle_url(client_config, remote_name)
    if remote_name == remote_url:
        logger.info(f'Current remote is "{remote_name}"')
    else:
        logger.info(f'Current remote is "{remote_name}" - {remote_url}')


def set_config_setting(setting_name: str, setting_value: str):
    client_config = load_client_config()
    config_dict = client_config.dict()

    assert setting_name in config_dict, f'client config doesn\'t have setting named {setting_name}'
    config_dict[setting_name] = setting_value
    with wrap_context('converting setting to target data type'):
        client_config = ClientConfig.parse_obj(config_dict)

    save_client_config(client_config)


def set_config_url_alias(alias: str, lifecycle_url: str):
    """Set up an alias for Lifecycle URL"""
    client_config = load_client_config()
    lifecycle_url = trim_url(lifecycle_url)
    client_config.lifecycle_url_aliases[alias] = lifecycle_url
    logger.info(f'Alias "{alias}" set to Racetrack URL {lifecycle_url}')
    save_client_config(client_config)
