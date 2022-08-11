from lifecycle.config import Config
from racetrack_commons.urls import get_external_pub_url


def get_fatman_pub_url(fatman_name: str, fatman_version: str, config: Config) -> str:
    """Build URL where fatman can be accessed through PUB"""
    return f'{get_external_pub_url(config.external_pub_url)}/fatman/{fatman_name}/{fatman_version}'
