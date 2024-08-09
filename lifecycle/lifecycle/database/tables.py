from dataclasses import dataclass
from datetime import datetime

from lifecycle.database.table_model import TableModel


@dataclass
class JobFamilyRecord(TableModel):
    class Metadata:
        table_name = 'registry_jobfamily'

    id: str
    name: str


@dataclass
class AuthUserRecord(TableModel):
    class Metadata:
        table_name = 'auth_user'

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
