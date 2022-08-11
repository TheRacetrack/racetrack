import os


def debug_mode_enabled() -> bool:
    return is_env_flag_enabled('DEBUG', 'false')


def is_env_flag_enabled(flag_name: str, default: str = 'false') -> bool:
    return os.environ.get(flag_name, default).lower() in {'true', 't', 'yes', 'y', '1'}


def is_deployment_local() -> bool:
    """Return whether this service is run locally outside of a container"""
    return os.environ.get('DEPLOYMENT_TYPE') == 'localhost'
