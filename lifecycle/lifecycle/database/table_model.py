from abc import ABC
from dataclasses import asdict, is_dataclass
import json
from typing import Any, ClassVar, Protocol
import uuid

from racetrack_client.log.context_error import ContextError


class IsDataclass(Protocol):
    """Type alias for a dataclass instance"""

    __dataclass_fields__: ClassVar[dict[str, Any]]


class TableModel(ABC):

    @classmethod
    def table_name(cls) -> str:
        metadata = getattr(cls, 'Metadata')
        assert metadata is not None, f'Metadata class not specified in {cls}'
        table_name = getattr(metadata, 'table_name')
        assert metadata is not None, f'table_name not specified in {cls}.Metadata'
        return table_name
    
    @classmethod
    def type_name(cls) -> str:
        return cls.__name__

    @classmethod
    def primary_key_columns(cls) -> list[str]:
        metadata = getattr(cls, 'Metadata')
        assert metadata is not None, f'Metadata class not specified in {cls}'
        primary_key = getattr(metadata, 'primary_key')
        assert metadata is not None, f'primary_key not specified in {cls}.Metadata'
        assert len(primary_key), f'primary_key of {cls} should consist of at least one column'
        return primary_key

    def primary_keys(self) -> list:
        columns = self.primary_key_columns()
        for column in columns:
            if not hasattr(self, column):
                raise ValueError(f'record has no field {column}')
        return [getattr(self, column) for column in columns]

    @classmethod
    def fields(cls) -> list[str]:
        field_annotations: dict[str, type] = cls.__annotations__
        return list(field_annotations.keys())

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> 'TableModel':
        return cls(**row)

    def to_row(self: IsDataclass) -> dict[str, Any]:
        if is_dataclass(self):
            return asdict(self)
        raise ValueError(f"'{self.__class__.__name__}' is not a dataclass!")


def new_uuid() -> str:
    return str(uuid.uuid4())


def parse_json_column(text: str | None) -> Any:
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ContextError('Unparsable JSON content') from e
