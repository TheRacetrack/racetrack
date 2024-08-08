from abc import ABC
from typing import Any, Self
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid
    

class TableModel(ABC):
    def __init__(self, **row_data):
        for field_name, value in row_data.items():
            setattr(self, field_name, value)
    
    @classmethod
    def table_name(cls) -> str:
        metadata = getattr(cls, 'Metadata')
        assert metadata is not None, f'Metadata class not specified in {cls}'
        table_name = getattr(metadata, 'table_name')
        assert metadata is not None, f'table_name not specified in {cls}.Metadata'
        return table_name
    
    @classmethod
    def fields(cls) -> list[str]:
        field_annotations: dict[str, type] = cls.__annotations__
        return list(field_annotations.keys())

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Self:
        return cls(**row)

    def to_row(self) -> dict[str, Any]:
        return asdict(self)  # type: ignore


def new_uuid() -> str:
    return str(uuid.uuid4())


@dataclass
class JobFamilyTable(TableModel):
    class Metadata:
        table_name = 'registry_jobfamily'

    id: str
    name: str


@dataclass
class AuthUserTable(TableModel):
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
