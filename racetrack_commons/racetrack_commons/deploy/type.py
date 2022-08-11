from enum import Enum


class DeployerType(Enum):
    DOCKER = 'docker'
    KUBERNETES = 'kubernetes'
