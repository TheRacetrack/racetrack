from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Extra, validator

from racetrack_client.utils.quantity import Quantity


class PythonManifest(BaseModel, extra=Extra.forbid):
    requirements_path: Optional[str] = None
    # path to a Python file with a entrypoint class
    entrypoint_path: str = ''
    # base name of Python entrypoint class
    entrypoint_class: str = ''


class GoManifest(BaseModel, extra=Extra.forbid):
    # relative path to Go modules requirements
    gomod: str = 'go.mod'


class GitManifest(BaseModel, extra=Extra.forbid):
    # URL of git remote: HTTPS, SSH or directory path to a remote repository
    remote: str
    branch: Optional[str] = None
    # subdirectory relative to git repo root
    directory: str = '.'


class DockerManifest(BaseModel, extra=Extra.forbid):
    dockerfile_path: Optional[str] = None


class ResourcesManifest(BaseModel, extra=Extra.forbid, arbitrary_types_allowed=True):
    # minimum memory amount in bytes, eg. 256Mi
    memory_min: Optional[Quantity] = None
    # maximum memory amount in bytes, eg. 1Gi
    memory_max: Optional[Quantity] = None
    # minimum CPU consumption in cores, eg. 10m
    cpu_min: Optional[Quantity] = None
    # maximum CPU consumption in cores, eg. 1000m
    cpu_max: Optional[Quantity] = None


    @validator(
        'memory_min', 
        'memory_max', 
        'cpu_min',
        'cpu_max',
        pre=True)
    def _validate_quantity(cls, v):
        if v is None:
            return None
        return Quantity(str(v))


class Manifest(BaseModel, extra=Extra.forbid, arbitrary_types_allowed=True):
    """Job Manifest file - build recipe to get deployable image from source code workspace"""

    # name of the Job Workload
    name: str

    # email address of the Job's owner to reach out
    owner_email: str

    git: GitManifest

    # version of the Job
    version: str = '0.0.1'

    # Language wrapper used to embed model
    lang: str = 'python3'

    # relative path to base manifest file, which will be extended by this manifest
    extends: Optional[str] = None

    # Python-specific configuration
    python: Optional[PythonManifest] = None

    # Go/Golang-specific configuration
    golang: Optional[GoManifest] = None

    # Docker-specific configuration
    docker: Optional[DockerManifest] = None

    # type of deployed image: docker image, packer, AMI
    image_type: str = 'docker'

    # system-wide packages that should be installed with apt
    system_dependencies: Optional[List[str]] = None

    # env vars for building
    build_env: Optional[Dict[str, str]] = None
    # env vars for runtime
    runtime_env: Optional[Dict[str, str]] = None
    # secret env vars loaded from an external file applied on building
    secret_build_env_file: Optional[str] = None
    # secret env vars loaded from an external file applied at runtime
    secret_runtime_env_file: Optional[str] = None

    # labels - job metadata for humans
    labels: Optional[Dict[str, Any]] = None

    # list of public job endpoints that can be accessed without authentication
    public_endpoints: Optional[List[str]] = None

    # number of instances of the Job
    replicas: int = 1

    # resources demands to allocate to the Job
    resources: Optional[ResourcesManifest] = None

    # Language wrapper attributes
    wrapper_properties: Optional[Dict[str, Any]] = None

    # Back-end platform where to deploy the service
    infrastructure_target: Optional[str] = None
