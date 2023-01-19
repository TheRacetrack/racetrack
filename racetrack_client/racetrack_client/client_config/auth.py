from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.client_config import ClientConfig
from racetrack_client.client_config.io import load_client_config, save_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.auth import is_auth_required, validate_user_auth, AuthError

logger = get_logger(__name__)


def login_user_auth(lifecycle_url: str, user_auth: str):
    client_config: ClientConfig = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    username = validate_user_auth(lifecycle_url, user_auth)
    set_user_auth(client_config, lifecycle_url, user_auth)
    save_client_config(client_config)
    logger.info(f'Logged as user {username} to Racetrack: {lifecycle_url}')


def logout_user_auth(lifecycle_url: str):
    client_config: ClientConfig = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    set_user_auth(client_config, lifecycle_url, "")
    save_client_config(client_config)
    logger.info(f'Logged out from Racetrack: {lifecycle_url}')


def set_user_auth(client_config: ClientConfig, lifecycle_url: str, user_auth: str):
    """
    You need to save the resulting config if you want to make changes persist
    """
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)

    if len(user_auth) == 0:
        if lifecycle_url in client_config.user_auths:
            del client_config.user_auths[lifecycle_url]
        else:
            raise RuntimeError(f'Missing {lifecycle_url} in Racetrack logged servers')
    else:
        client_config.user_auths[lifecycle_url] = user_auth


def get_user_auth(client_config: ClientConfig, lifecycle_url: str) -> str:
    if lifecycle_url in client_config.user_auths:
        return client_config.user_auths[lifecycle_url]

    if is_auth_required(lifecycle_url):
        raise AuthError(f"missing auth token for {lifecycle_url}. You need to do: racetrack login <token> --remote {lifecycle_url}")

    return ''
