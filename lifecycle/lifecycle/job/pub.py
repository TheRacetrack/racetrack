from lifecycle.config import Config
from racetrack_commons.urls import get_external_pub_url


def get_job_pub_url(job_name: str, job_version: str, config: Config) -> str:
    """Build URL where job can be accessed through PUB"""
    return f'{get_external_pub_url(config.external_pub_url)}/job/{job_name}/{job_version}'
