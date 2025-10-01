import os

from racetrack_client.utils.env import is_env_flag_enabled


def debug_mode_enabled() -> bool:
    return is_env_flag_enabled('DEBUG', 'false')


def is_deployment_local() -> bool:
    """Return whether this service is run locally outside of a container"""
    return os.environ.get('DEPLOYMENT_TYPE') == 'localhost'
