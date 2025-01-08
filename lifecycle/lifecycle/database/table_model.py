from abc import ABC
from dataclasses import asdict, is_dataclass
import json
from typing import Any, Type, Callable
import uuid

from racetrack_client.log.context_error import ContextError


class TableModel(ABC):
    class Metadata:
        table_name: str
        primary_key: str  # name of the column being used as primary key
        primary_key_type: type = str  # type of the primary key column
        # mapping of a foreign key column to table class
        # It indicates that this model depends on the other and should be deleted along with the foreign one
        on_delete_cascade: dict[str, 'TableModel'] = {}
        plural_name: str | None = None
        # list of columns to display on the management view
        list_display_columns: list[str] = []
        # function to generate a new value for the primary key column
        primary_key_generator: Callable[[], Any] | None = None


def table_type_name(cls: Type[TableModel] | TableModel) -> str:
    if isinstance(cls, TableModel):
        return cls.__class__.__name__
    return cls.__name__


def table_name(cls: Type[TableModel] | TableModel) -> str:
    if isinstance(cls, TableModel):
        cls = cls.__class__
    metadata = table_metadata(cls)
    _table_name = getattr(metadata, 'table_name')
    assert metadata is not None, f'table_name not specified in {cls}.Metadata'
    return _table_name


def table_primary_key_column(cls: Type[TableModel] | TableModel) -> str:
    if isinstance(cls, TableModel):
        cls = cls.__class__
    metadata = table_metadata(cls)
    primary_key = getattr(metadata, 'primary_key')
    assert metadata is not None, f'primary_key not specified in {cls}.Metadata'
    assert isinstance(primary_key, str), f'primary_key of {cls} should be a string column name'
    return primary_key


def table_primary_key_type(cls: Type[TableModel]) -> type:
    if isinstance(cls, TableModel):
        cls = cls.__class__
    metadata = table_metadata(cls)
    return getattr(metadata, 'primary_key_type') or str


def primary_key_value(self: TableModel) -> Any:
    """Return the value of the primary key field"""
    column = table_primary_key_column(self)
    if not hasattr(self, column):
        raise ValueError(f'record has no primary key field {column}')
    return getattr(self, column)


def table_on_delete_cascade(cls: Type[TableModel] | TableModel) -> dict[str, type[TableModel]]:
    metadata = table_metadata(cls)
    return getattr(metadata, 'on_delete_cascade', {})


def table_fields(cls: Type[TableModel] | TableModel) -> list[str]:
    if isinstance(cls, TableModel):
        cls = cls.__class__
    field_annotations: dict[str, type] = cls.__annotations__
    return list(field_annotations.keys())


def record_to_dict(self: TableModel) -> dict[str, Any]:
    if is_dataclass(self):
        return asdict(self)
    raise ValueError(f"'{self.__class__.__name__}' is not a dataclass!")


def table_metadata(cls: Type[TableModel] | TableModel) -> TableModel.Metadata:
    if isinstance(cls, TableModel):
        cls = cls.__class__
    metadata = getattr(cls, 'Metadata')
    assert metadata is not None, f'Metadata class not specified in {cls}'
    return metadata


def table_plural_name(cls: Type[TableModel]) -> str:
    metadata = table_metadata(cls)
    plural_name = getattr(metadata, 'plural_name')
    return plural_name or (table_name(cls) + 's')


def table_list_display_columns(cls: Type[TableModel]) -> list[str]:
    metadata = table_metadata(cls)
    list_display_columns = getattr(metadata, 'list_display_columns')
    return list_display_columns or []


def table_primary_key_generator(cls: Type[TableModel]) -> Callable[[], str] | None:
    metadata = table_metadata(cls)
    return getattr(metadata, 'primary_key_generator', None)


def new_uuid() -> str:
    return str(uuid.uuid4())


def parse_json_column(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ContextError(f'Unparsable JSON content ({text})') from e
