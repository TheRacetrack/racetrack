import os


def is_env_flag_enabled(flag_name: str, default: str = 'false') -> bool:
    return os.environ.get(flag_name, default).lower() in {'true', 't', 'yes', 'y', '1'}
