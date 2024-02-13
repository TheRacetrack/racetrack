from enum import Enum
from typing import Optional

from pydantic import BaseModel, ValidationError, field_validator
import pytest

from racetrack_client.utils.datamodel import parse_dict_datamodel
from racetrack_client.utils.quantity import Quantity


class DeployerType(Enum):
    DOCKER = 'docker'
    KUBERNETES = 'kubernetes'


class Config(BaseModel, extra='forbid', arbitrary_types_allowed=True):
    log_level: str = 'info'
    http_port: int = 7202
    deployer: DeployerType = DeployerType.DOCKER
    memory_min: Optional[Quantity] = None
    memory_max: Optional[Quantity] = None

    @field_validator('memory_min', 'memory_max', mode='before')
    @classmethod
    def _memory_min_must_be_valid_quantity(cls, v: str) -> Optional[Quantity]:
        if v is None:
            return None
        return Quantity(str(v))


def test_parse_enum_in_datamodel():
    datamodel = parse_dict_datamodel({}, Config)

    assert datamodel.log_level == 'info'
    assert datamodel.memory_min is None
    assert datamodel.deployer == DeployerType.DOCKER
    assert datamodel.deployer.value == 'docker'
    
    obj = {
        'log_level': 'debug',
        'deployer': 'kubernetes'
    }
    datamodel = parse_dict_datamodel(obj, Config)
    assert datamodel.log_level == 'debug'
    assert datamodel.deployer == DeployerType.KUBERNETES


def test_parse_wrong_enum_in_datamodel():
    obj = {
        'deployer': 'none_of_these'
    }
    with pytest.raises(ValidationError):
        parse_dict_datamodel(obj, Config)


def test_parse_internal_type():
    obj = {
        'memory_min': '10Ki',
        'memory_max': '1k',
    }
    datamodel = parse_dict_datamodel(obj, Config)
    assert datamodel.memory_min.plain_number == 10240
    assert datamodel.memory_max.plain_number == 1000
