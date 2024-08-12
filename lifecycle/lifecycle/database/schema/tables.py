from dataclasses import dataclass
from datetime import datetime

from lifecycle.database.table_model import TableModel


@dataclass
class JobFamilyRecord(TableModel):
    """Collection of Jobs generations with the same name (family name)"""
    class Metadata:
        table_name = 'registry_jobfamily'
        primary_key = ['id']

    id: str
    name: str


@dataclass
class JobRecord(TableModel):
    class Metadata:
        table_name = 'registry_job'
        primary_key = ['id']

    id: str
    family_id: str  # foreign key: JobFamilyRecord
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
    # internal hostnames of the job replicas (eg. pods)
    replica_internal_names: str | None
    # exact name and version of a job type used to build this job
    job_type_version: str
    # Statistics of a Job seen by infrastructure
    infrastructure_stats: str | None


@dataclass
class DeploymentRecord(TableModel):
    class Metadata:
        table_name = 'registry_deployment'
        primary_key = ['id']

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


@dataclass
class EscRecord(TableModel):
    class Metadata:
        table_name = 'registry_esc'
        primary_key = ['id']

    id: str
    name: str


@dataclass
class PublicEndpointRecord(TableModel):
    class Metadata:
        table_name = 'registry_publicendpointrequest'
        primary_key = ['id']

    id: str
    job_id: str  # foreign key: JobRecord
    endpoint: str
    active: bool


@dataclass
class TrashJobRecord(TableModel):
    class Metadata:
        table_name = 'registry_trashjob'
        primary_key = ['id']

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
class AuditLogEventRecord(TableModel):
    class Metadata:
        table_name = 'registry_auditlogevent'
        primary_key = ['id']

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
class AuthSubjectRecord(TableModel):
    class Metadata:
        table_name = 'registry_authsubject'
        primary_key = ['id']

    id: str
    user_id: int | None  # foreign key: AuthUserRecord
    esc_id: str | None  # foreign key: EscRecord
    job_family_id: str | None  # foreign key: JobFamilyRecord


@dataclass
class AuthTokenRecord(TableModel):
    class Metadata:
        table_name = 'registry_authtoken'
        primary_key = ['id']

    id: str
    auth_subject_id: str  # foreign key: AuthSubjectRecord
    token: str  # JWT token
    expiry_time: datetime | None
    active: bool
    # last day the token was used for authentication
    last_use_time: datetime | None


@dataclass
class AuthResourcePermissionRecord(TableModel):
    class Metadata:
        table_name = 'registry_authresourcepermission'
        primary_key = ['id']

    id: int
    auth_subject_id: str  # foreign key: AuthSubjectRecord
    # operation permitted to the subject
    scope: str
    # resource-scope: anything, job family, job, endpoint
    job_family_id: str | None  # foreign key: JobFamilyRecord
    job_id: str | None  # foreign key: JobRecord
    endpoint: str | None


@dataclass
class SettingRecord(TableModel):
    class Metadata:
        table_name = 'registry_setting'
        primary_key = ['name']

    name: str
    value: str | None


@dataclass
class AsyncJobCallRecord(TableModel):
    class Metadata:
        table_name = 'registry_asyncjobcall'
        primary_key = ['id']

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
    request_headers: str | None
    request_body: bytes
    response_status_code: int | None
    response_headers: str | None
    response_body: bytes
    attempts: int
    pub_instance_addr: str
    retriable_error: bool


@dataclass
class AuthUserRecord(TableModel):
    class Metadata:
        table_name = 'auth_user'
        primary_key = ['id']

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
