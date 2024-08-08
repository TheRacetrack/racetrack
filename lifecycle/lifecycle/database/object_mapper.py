from typing import Any, Type, TypeVar

from lifecycle.database.engine import DbEngine
from lifecycle.database.postgres.query_builder import QueryBuilder

from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger
from lifecycle.database.tables import TableModel
from lifecycle.database.type_parser import parse_typed_object

logger = get_logger(__name__)

T = TypeVar("T", bound=TableModel)


class ObjectMapper:

    def __init__(self, engine: DbEngine):
        self.engine: DbEngine = engine
        self.query_builder: QueryBuilder = QueryBuilder()

    def find_one(
        self,
        table_type: Type[T],
        filters: dict[str, Any],
    ) -> T:
        assert filters, 'filters should contain at least one criteria'
        placeholder = self.engine.placeholder()
        filter_conditions = [f'{field} = {placeholder}' for field in filters.keys()]
        filter_params = list(filters.values())

        row = self.engine.select_one(
            table=table_type.table_name(),
            fields=table_type.fields(),
            filter_conditions=filter_conditions,
            filter_params=filter_params,
        )
        if row is None:
            columns = ', '.join(filters.keys())
            raise EntityNotFound(f'{table_type.table_name()} record not found for given {columns}')

        return _convert_row_to_object(row, table_type)

    def list_all(
        self,
        table_type: Type[T],
        order_by: list[str] | None = None,
    ) -> list[T]:
        rows = self.engine.select_many(
            table=table_type.table_name(),
            fields=table_type.fields(),
            order_by=order_by,
        )
        return [_convert_row_to_object(row, table_type) for row in rows]

    def create(
        self,
        record_object: TableModel,
    ):
        fields: list[str] = record_object.fields()
        data = {}
        for field in fields:
            if not hasattr(record_object, field):
                raise ValueError(f'given table model {type(record_object).__name__} has no field {field}')
            data[field] = getattr(record_object, field)
        self.engine.insert_one(
            table=record_object.table_name(),
            data=data,
        )


def _convert_row_to_object(
    row: dict[str, Any],
    table_type: Type[T],
) -> T:
    return parse_typed_object(row, table_type)
