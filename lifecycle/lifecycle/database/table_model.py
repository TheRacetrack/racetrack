from abc import ABC
from dataclasses import asdict, is_dataclass
import json
from typing import Any
import uuid

from racetrack_client.log.context_error import ContextError


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
    def primary_key_column(cls) -> str:
        metadata = getattr(cls, 'Metadata')
        assert metadata is not None, f'Metadata class not specified in {cls}'
        primary_key = getattr(metadata, 'primary_key')
        assert metadata is not None, f'primary_key not specified in {cls}.Metadata'
        assert isinstance(primary_key, str), f'primary_key of {cls} should be a string column name'
        return primary_key

    def primary_key_value(self) -> Any:
        """Return the value of the primary key field"""
        column = self.primary_key_column()
        if not hasattr(self, column):
            raise ValueError(f'record has no primary key field {column}')
        return getattr(self, column)
    
    @classmethod
    def on_delete_cascade(cls) -> dict[str, type['TableModel']]:
        metadata = getattr(cls, 'Metadata')
        assert metadata is not None, f'Metadata class not specified in {cls}'
        return getattr(metadata, 'on_delete_cascade', {})

    @classmethod
    def fields(cls) -> list[str]:
        field_annotations: dict[str, type] = cls.__annotations__
        return list(field_annotations.keys())

    def to_row(self) -> dict[str, Any]:
        if is_dataclass(self):
            return asdict(self)
        raise ValueError(f"'{self.__class__.__name__}' is not a dataclass!")


def new_uuid() -> str:
    return str(uuid.uuid4())


def parse_json_column(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ContextError(f'Unparsable JSON content ({text})') from e
