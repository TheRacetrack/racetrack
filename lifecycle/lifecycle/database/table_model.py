from abc import ABC
from dataclasses import asdict, is_dataclass
from typing import Any, Type, Callable
import uuid


class TableModel(ABC):
    class Metadata:
        table_name: str  # name of the table in the database
        primary_key_column: str  # name of the column being used as primary key
        primary_key_type: type = str  # type of the primary key column, e.g. str | int
        # function to generate a new value for the primary key column
        primary_key_generator: Callable[[], Any] | None = None
        # mapping of a foreign key column to a foreign table class
        # It indicates this model depends on the other, and it should be deleted along with the foreign one
        on_delete_cascade: dict[str, Type['TableModel']] = {}
        plural_name: str
        # list of columns to display on the management view
        main_columns: list[str] = []

        # Attributes evaluated at runtime:
        fields: list[str]


def table_type_name(cls: Type[TableModel] | TableModel) -> str:
    if isinstance(cls, TableModel):
        return type(cls).__name__
    return cls.__name__


def table_metadata(cls: Type[TableModel] | TableModel) -> TableModel.Metadata:
    if isinstance(cls, TableModel):
        cls = type(cls)
    metadata: TableModel.Metadata = getattr(cls, 'Metadata', None)
    assert metadata is not None, f'Metadata class not specified in {cls}'

    field_annotations: dict[str, type] = cls.__annotations__
    metadata.fields = list(field_annotations.keys())

    _table_name = getattr(metadata, 'table_name', None)
    assert _table_name, f'table_name not specified in {cls}.Metadata'
    primary_key_column = getattr(metadata, 'primary_key_column', None)
    assert primary_key_column, f'primary_key_column not specified in {cls}.Metadata'
    assert isinstance(primary_key_column, str), f'{cls}.Metadata.primary_key_column should be a string column name'
    assert primary_key_column in metadata.fields, f'{cls}.Metadata.primary_key_column "{primary_key_column}" not found in {cls} fields'

    metadata.primary_key_type = getattr(metadata, 'primary_key_type', None) or str
    metadata.on_delete_cascade = getattr(metadata, 'on_delete_cascade', {})
    metadata.plural_name = getattr(metadata, 'plural_name', None) or (cls.__name__ + 's')
    metadata.main_columns = getattr(metadata, 'main_columns', [])
    metadata.primary_key_generator = getattr(metadata, 'primary_key_generator', None)
    return metadata


def get_primary_key_value(self: TableModel) -> Any:
    """Return the value of the primary key field"""
    metadata = table_metadata(self)
    column = metadata.primary_key_column
    if not hasattr(self, column):
        raise ValueError(f'record has no primary key field {column}')
    return getattr(self, column, None)


def record_to_dict(self: TableModel) -> dict[str, Any]:
    if is_dataclass(self):
        return asdict(self)
    raise ValueError(f"'{self.__class__.__name__}' is not a dataclass!")


def new_uuid() -> str:
    return str(uuid.uuid4())
