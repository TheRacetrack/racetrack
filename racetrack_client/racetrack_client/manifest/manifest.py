from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field

from racetrack_client.utils.quantity import AnnotatedQuantity

from logging import Logger

class GitManifest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # URL of git remote: HTTPS, SSH or directory path to a remote repository
    remote: str
    branch: Optional[str] = None
    # subdirectory relative to git repo root
    directory: str = '.'


class ResourcesManifest(BaseModel):
    model_config = ConfigDict(extra='forbid', arbitrary_types_allowed=True)

    # minimum memory amount in bytes, eg. 256Mi
    memory_min: Optional[AnnotatedQuantity] = None
    # maximum memory amount in bytes, eg. 1Gi
    memory_max: Optional[AnnotatedQuantity] = None
    # minimum CPU consumption in cores, eg. 10m
    cpu_min: Optional[AnnotatedQuantity] = None
    # maximum CPU consumption in cores, eg. 1000m
    cpu_max: Optional[AnnotatedQuantity] = None


class Manifest(BaseModel):
    """Job Manifest file - build recipe to get deployable image from source code workspace"""
    model_config = ConfigDict(extra='forbid', arbitrary_types_allowed=True, populate_by_name=True)

    # name of the Job Workload
    name: str

    # email address of the Job's owner to reach out
    owner_email: str

    git: GitManifest

    # version of the Job
    version: str = '0.0.1'

    # Jobtype wrapper used to embed model
    jobtype: Optional[str] = None
    lang: Optional[str] = None  # Deprecated

    # relative path to base manifest file, which will be extended by this manifest
    extends: Optional[str] = None

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

    # Extra parameters specified by the jobtype
    jobtype_extra: Optional[Dict[str, Any]] = None
    golang: Optional[Dict[str, Any]] = None  # Deprecated
    python: Optional[Dict[str, Any]] = None  # Deprecated
    docker: Optional[Dict[str, Any]] = None  # Deprecated
    wrapper_properties: Optional[Dict[str, Any]] = None  # Deprecated

    # Back-end platform where to deploy the service
    infrastructure_target: Optional[str] = None

    # original YAML string from which the manifest was parsed, field for internal use only
    origin_yaml_: Optional[str] = Field(None, exclude=True)
    # original dictionary from which the manifest was parsed, field for internal use only
    origin_dict_: Optional[Dict[str, Any]] = Field(None, exclude=True)

    # This is the "source of truth for deprications", schema.json has to follow this
    deprecated_fields: Dict[str, Any] = {
        'lang': '`jobtype:`',
        'golang': '`jobtype_extra:`',
        'python': '`jobtype_extra:`',
        'docker': '`jobtype_extra:`',
        'wrapper_properties': '`jobtype_extra:`'
    }

    def get_jobtype(self):
        return self.jobtype if self.jobtype else self.lang


    def get_jobtype_extra(self):
        for field in [self.jobtype_extra, self.golang, self.python, self.wrapper_properties]:
            if field is not None:
                return field


    def warn_if_using_deprecated_fields(self, logger: Logger):
        for field, replacement in self.deprecated_fields.items():
            if getattr(self, field) is not None:
                logger.warning(f'`{field}:` is deprecated. Use {replacement} instead.')
