import os
from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel
import yaml

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def load_config(clazz: Type[T]) -> T:
    """
    Load general configuration from YAML file given in CONFIG_FILE environment var or load default config.
    :param clazz: pydantic.BaseModel type that should be loaded
    :return: configuration object of given "clazz" type
    """
    config_file_path = os.environ.get('CONFIG_FILE')
    if not config_file_path:
        logger.warning('CONFIG_FILE unspecified, loading default config')
        return clazz()

    path = Path(config_file_path)
    if not path.is_file():
        raise FileNotFoundError(f"config file {config_file_path} doesn't exist")

    try:
        with path.open() as file:
            config_dict = yaml.load(file, Loader=yaml.FullLoader)
            config = clazz.parse_obj(config_dict)

            logger.info(f'config loaded from {config_file_path}: {config}')
            return config
    except Exception as e:
        raise RuntimeError('loading config failed') from e
