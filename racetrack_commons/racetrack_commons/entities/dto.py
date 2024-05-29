from enum import Enum
from typing import Dict, Optional, Any

from pydantic import BaseModel, ConfigDict

from racetrack_client.manifest import Manifest


class JobStatus(Enum):
    STARTING = 'starting'  # job created but didn't appear as ready in cluster yet, still initializing
    RUNNING = 'running'
    ERROR = 'error'  # found in cluster but has failing status
    ORPHANED = 'orphaned'  # found in cluster but Lifecycle doesn't recall creating it
    LOST = 'lost'  # expected but not found in cluster


class JobFamilyDto(BaseModel):
    name: str
    id: str | None = None


class JobDto(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    version: str
    status: str
    create_time: int
    update_time: int
    id: str | None = None
    manifest: Manifest | None = None
    manifest_yaml: str | None = None
    # placeholder for the name of the resource seen internally by a cluster
    # (may contain port number depending on cluster type)
    internal_name: str | None = None
    # public url of a job
    pub_url: str | None = None
    error: str | None = None
    notice: str | None = None
    image_tag: str | None = None
    # username of the last deployer
    deployed_by: str | None = None
    last_call_time: int | None = None
    infrastructure_target: str | None = None
    # internal hostnames of the job replicas (eg. pods)
    replica_internal_names: list[str] = []
    # exact name and version of a job type used to build this job
    job_type_version: str = ''
    # Statistics of a Job seen by infrastructure
    infrastructure_stats: dict[str, Any] = {}

    def __str__(self):
        return f'{self.name} v{self.version}'


class DeploymentStatus(Enum):
    IN_PROGRESS = 'in_progress'  # deployment started, still in progress
    DONE = 'done'  # job deployed successfully
    FAILED = 'failed'  # deployment failed with an error


class DeploymentDto(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    status: str
    create_time: int
    update_time: int
    error: Optional[str] = None
    job: Optional[JobDto] = None  # successfully deployed job related to it
    deployed_by: Optional[str] = None  # username of the last deployer
    phase: Optional[str] = None  # phase (step) of the deployment
    image_name: Optional[str] = None
    infrastructure_target: Optional[str] = None
    manifest_yaml: str  # manifest represented as YAML string
    job_name: str
    job_version: str


class EscDto(BaseModel):
    name: str
    id: Optional[str] = None


class UserProfileDto(BaseModel):
    username: str
    token: str
    is_staff: bool = False


class PublicEndpointRequestDto(BaseModel):
    job_name: str
    job_version: str
    endpoint: str
    active: bool


class AuditLogEventDto(BaseModel):
    id: str
    version: int
    timestamp: int
    event_type: str
    properties: Dict[str, Any]
    username_executor: Optional[str] = None
    username_subject: Optional[str] = None
    job_name: Optional[str] = None
    job_version: Optional[str] = None


class AsyncJobCallStatus(Enum):
    ONGOING = 'ongoing'  # job call in progress
    COMPLETED = 'completed'  # done with a successful result
    FAILED = 'failed'  # aborted to due error


class AsyncJobCallDto(BaseModel):
    id: str
    status: str
    started_at: int  # timestamp in milliseconds
    ended_at: int | None  # timestamp in milliseconds
    error: str | None
    job_name: str
    job_version: str
    job_path: str
    request_method: str
    request_url: str
    request_headers: dict[str, str]
    request_body: str
    response_status_code: int | None
    response_headers: dict[str, str] | None
    response_body: str
    attempts: int = 0
    pub_instance_addr: str
    retriable_error: bool
