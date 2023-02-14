from enum import Enum
from typing import Dict, Optional, List

from pydantic import BaseModel

from racetrack_client.manifest import Manifest


class JobStatus(Enum):
    CREATED = 'created'  # job created but didnt appear in cluster yet
    RUNNING = 'running'
    ERROR = 'error'  # found in cluster but has failing status
    ORPHANED = 'orphaned'  # found in cluster but LC doesn't recall to create that
    LOST = 'lost'  # expected but not found in cluster


class JobFamilyDto(BaseModel):
    name: str
    id: Optional[str] = None


class JobDto(BaseModel, arbitrary_types_allowed=True):
    name: str
    version: str
    status: str
    create_time: int
    update_time: int
    id: Optional[str] = None
    manifest: Optional[Manifest] = None
    # placeholder for the name of the resource seen internally by a cluster
    # (may contain port number depending on cluster type)
    internal_name: Optional[str] = None
    # public url of a job
    pub_url: Optional[str] = None
    error: Optional[str] = None
    image_tag: Optional[str] = None
    # username of the last deployer
    deployed_by: Optional[str] = None
    last_call_time: Optional[int] = None
    infrastructure_target: Optional[str] = None

    def __str__(self):
        return f'{self.name} v{self.version}'


class DeploymentStatus(Enum):
    IN_PROGRESS = 'in_progress'  # deployment started, still in progress
    DONE = 'done'  # job deployed successfully
    FAILED = 'failed'  # deployment failed with an error


class DeploymentDto(BaseModel, arbitrary_types_allowed=True):
    id: str
    status: str
    error: Optional[str] = None
    job: Optional[JobDto] = None  # successfully deployed job related to it
    deployed_by: Optional[str] = None  # username of the last deployer
    phase: Optional[str] = None  # phase (step) of the deployment
    image_name: Optional[str] = None
    infrastructure_target: Optional[str] = None


class EscDto(BaseModel):
    name: str
    id: Optional[str] = None


class UserProfileDto(BaseModel):
    username: str
    token: str


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
    properties: Optional[Dict] = None
    username_executor: Optional[str] = None
    username_subject: Optional[str] = None
    job_name: Optional[str] = None
    job_version: Optional[str] = None
