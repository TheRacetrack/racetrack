from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.request import Requests, parse_response_object

logger = get_logger(__name__)


def get_current_remote(quiet: bool):
    client_config = load_client_config()
    remote_name = client_config.lifecycle_url
    lifecycle_url = resolve_lifecycle_url(client_config, remote_name)
    if quiet:
        print(lifecycle_url)
    elif remote_name == lifecycle_url:
        logger.info(f'Current remote is "{lifecycle_url}"')
    else:
        logger.info(f'Current remote is "{remote_name}", resolving to {lifecycle_url}')


def get_current_pub_address(quiet: bool):
    client_config = load_client_config()
    remote_name = client_config.lifecycle_url
    lifecycle_url = resolve_lifecycle_url(client_config, remote_name)

    r = Requests.get(
        f'{lifecycle_url}/api/v1/info',
    )
    response = parse_response_object(r, 'Lifecycle response error')
    pub_url = response.get('external_pub_url')
    assert pub_url, 'Pub URL is not specified by the Racetrack server'
    if quiet:
        print(pub_url)
    else:
        logger.info(f'Current Pub URL is: {pub_url}')
