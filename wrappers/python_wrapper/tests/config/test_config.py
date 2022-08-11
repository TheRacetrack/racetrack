import os

import pytest

from fatman_wrapper.config import Config
from racetrack_client.utils.config import load_config


def test_loading_default_config():
    config: Config = load_config(Config)
    assert config.http_port == 7000


def test_loading_config_from_yaml():
    os.environ['CONFIG_FILE'] = 'config/sample.yaml'
    config: Config = load_config(Config)

    assert config.http_port == 80, 'value overriden'
    assert config.http_addr == '0.0.0.0', 'default value set for missing variables'


def test_loading_not_existing_config():
    os.environ['CONFIG_FILE'] = 'config/not-existing-at-all.yaml'
    with pytest.raises(FileNotFoundError):
        load_config(Config)


def test_loading_invalid_config():
    os.environ['CONFIG_FILE'] = 'config/invalid.yaml'
    with pytest.raises(RuntimeError):
        load_config(Config)
