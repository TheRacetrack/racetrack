from dataclasses import dataclass
from datetime import datetime

from lifecycle.database.table_model import TableModel


@dataclass
class JobFamily(TableModel):
    """Collection of Jobs generations with the same name (family name)"""
    class Metadata:
        table_name = 'registry_jobfamily'
        primary_key = 'id'

    id: str
    name: str

    def __str__(self):
        return f'{self.name}'


@dataclass
class Job(TableModel):
    class Metadata:
        table_name = 'registry_job'
        primary_key = 'id'
        on_delete_cascade = {
            'family_id': JobFamily,
        }

    id: str
    family_id: str  # foreign key: JobFamily
    name: str
    version: str
    status: str
    create_time: datetime
    update_time: datetime
    manifest: str | None
    internal_name: str | None
    error: str | None
    notice: str | None
    image_tag: str | None
    deployed_by: str | None
    last_call_time: datetime | None
    infrastructure_target: str | None
    # internal hostnames of the job replicas (e.g. pods)
    replica_internal_names: str | None
    # exact name and version of a job type used to build this job
    job_type_version: str
    # Statistics of a Job seen by infrastructure, JSON
    infrastructure_stats: str | None

    def __str__(self):
        return f'{self.name} {self.version}'


@dataclass
class Deployment(TableModel):
    class Metadata:
        table_name = 'registry_deployment'
        primary_key = 'id'

    id: str
    status: str
    create_time: datetime
    update_time: datetime
    manifest: str
    error: str | None
    job_name: str
    job_version: str
    deployed_by: str | None
    build_logs: str | None
    phase: str | None
    image_name: str | None
    infrastructure_target: str | None
    warnings: str | None

    def __str__(self):
        return f'{self.id}'


@dataclass
class Esc(TableModel):
    class Metadata:
        table_name = 'registry_esc'
        primary_key = 'id'

    id: str
    name: str

    def __str__(self):
        return f'{self.name} ({self.id})'


@dataclass
class PublicEndpointRequest(TableModel):
    class Metadata:
        table_name = 'registry_publicendpointrequest'
        primary_key = 'id'
        on_delete_cascade = {
            'job_id': Job,
        }

    id: str
    job_id: str  # foreign key: Job
    endpoint: str
    active: bool


@dataclass
class TrashJob(TableModel):
    class Metadata:
        table_name = 'registry_trashjob'
        primary_key = 'id'

    id: str
    name: str
    version: str
    status: str
    create_time: datetime
    update_time: datetime
    delete_time: datetime
    manifest: str | None
    internal_name: str | None
    error: str | None
    image_tag: str | None
    deployed_by: str | None
    last_call_time: datetime | None
    infrastructure_target: str | None
    age_days: float


@dataclass
class AuditLogEvent(TableModel):
    class Metadata:
        table_name = 'registry_auditlogevent'
        primary_key = 'id'

    id: str
    version: int  # data structure version
    timestamp: datetime
    event_type: str
    properties: str | None
    username_executor: str | None
    username_subject: str | None
    job_name: str | None
    job_version: str | None


@dataclass
class User(TableModel):
    class Metadata:
        table_name = 'auth_user'
        primary_key = 'id'

    id: int
    password: str
    last_login: datetime | None
    is_superuser: bool
    username: str
    last_name: str
    email: str
    is_staff: bool
    is_active: bool
    date_joined: datetime
    first_name: str


@dataclass
class AuthSubject(TableModel):
    class Metadata:
        table_name = 'registry_authsubject'
        primary_key = 'id'
        on_delete_cascade = {
            'user_id': User,
            'esc_id': Esc,
            'job_family_id': JobFamily,
        }

    id: str
    user_id: int | None  # foreign key: User
    esc_id: str | None  # foreign key: Esc
    job_family_id: str | None  # foreign key: JobFamily

    def __str__(self):
        if self.user_id is not None:
            return f'User: {self.user_id}'
        if self.esc_id is not None:
            return f'ESC: {self.esc_id}'
        if self.job_family_id is not None:
            return f'Job Family: {self.job_family_id}'
        return f'{self.id}'

    def subject_type(self) -> str:
        if self.user_id is not None:
            return 'User'
        if self.esc_id is not None:
            return 'ESC'
        if self.job_family_id is not None:
            return 'Job Family'
        return 'Unknown'


@dataclass
class AuthToken(TableModel):
    class Metadata:
        table_name = 'registry_authtoken'
        primary_key = 'id'
        on_delete_cascade = {
            'auth_subject_id': AuthSubject,
        }

    id: str
    auth_subject_id: str  # foreign key: AuthSubject
    token: str  # JWT token
    expiry_time: datetime | None
    active: bool
    # last day the token was used for authentication
    last_use_time: datetime | None


@dataclass
class AuthResourcePermission(TableModel):
    class Metadata:
        table_name = 'registry_authresourcepermission'
        primary_key = 'id'
        on_delete_cascade = {
            'auth_subject_id': AuthSubject,
            'job_family_id': JobFamily,
            'job_id': Job,
        }

    id: int | None
    auth_subject_id: str  # foreign key: AuthSubject
    # operation permitted to the subject
    scope: str
    # resource-scope: anything, job family, job, endpoint
    job_family_id: str | None  # foreign key: JobFamily
    job_id: str | None  # foreign key: Job
    endpoint: str | None


@dataclass
class Setting(TableModel):
    class Metadata:
        table_name = 'registry_setting'
        primary_key = 'name'

    name: str
    value: str | None  # JSON


@dataclass
class AsyncJobCall(TableModel):
    class Metadata:
        table_name = 'registry_asyncjobcall'
        primary_key = 'id'

    id: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    error: str | None
    job_name: str
    job_version: str
    job_path: str
    request_method: str
    request_url: str
    request_headers: str | None  # JSON
    request_body: bytes
    response_status_code: int | None
    response_headers: str | None  # JSON
    response_body: bytes
    attempts: int
    pub_instance_addr: str
    retriable_error: bool
    
    def __str__(self):
        return self.id


all_tables: list[type[TableModel]] = [
    JobFamily,
    Job,
    Deployment,
    Esc,
    PublicEndpointRequest,
    TrashJob,
    AuditLogEvent,
    User,
    AuthSubject,
    AuthToken,
    AuthResourcePermission,
    Setting,
    AsyncJobCall,
]
