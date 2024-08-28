from typing import Any, Type, TypeVar

from lifecycle.database.base_engine import DbEngine
from lifecycle.database.condition_builder import QueryCondition
from lifecycle.database.query_wrapper import QueryWrapper
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger
from lifecycle.database.table_model import TableModel
from lifecycle.database.schema.tables import all_tables
from lifecycle.database.type_parser import parse_typed_object

logger = get_logger(__name__)

T = TypeVar('T', bound=TableModel)


class RecordMapper:
    def __init__(self, engine: DbEngine):
        self.query_wrapper: QueryWrapper = QueryWrapper(engine)
        self.placeholder: str = engine.query_builder.placeholder()

    def find_one(
        self,
        table_type: Type[T],
        **filter_kwargs: Any,
    ) -> T:
        """
        Find a single record based on the given filter criteria
        :param table_type: table model class
        :param filter_kwargs: key-value pairs of filter criteria
        :raise EntityNotFound: if record is not found
        :return: record object
        """
        assert len(filter_kwargs), 'query should be filtered by at least one criteria'
        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)

        row = self.query_wrapper.select_one(
            table=table_type.table_name(),
            fields=table_type.fields(),
            filter_conditions=filter_conditions,
            filter_params=filter_params,
        )
        if row is None:
            filtered_by = ', '.join(filter_kwargs.keys())
            raise EntityNotFound(f'{table_type.__name__} record not found for given {filtered_by}')

        return _convert_row_to_record_model(row, table_type)

    def find_many(
        self,
        table_type: Type[T],
        order_by: list[str] | None = None,
        **filter_kwargs: Any,
    ) -> list[T]:
        """
        Find multiple records based on the given filter criteria (exact match only)
        :param table_type: table model class
        :param order_by: list of columns to order by, for descending order prepend column name with '-'
        :param filter_kwargs: key-value pairs of exact filter criteria
        :return: list of record objects
        """
        assert len(filter_kwargs), 'query should be filtered by at least one criteria'
        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)
        rows = self.query_wrapper.select_many(
            table=table_type.table_name(),
            fields=table_type.fields(),
            filter_conditions=filter_conditions,
            filter_params=filter_params,
            order_by=order_by,
        )
        return [_convert_row_to_record_model(row, table_type) for row in rows]
    
    def filter(
        self,
        table_type: Type[T],
        condition: QueryCondition,
        join_expression: str | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
    ) -> list[T]:
        """
        Filter by more sophisticated SQL condition (OR, AND, IS NULL, <, >= operators, etc.)
        :param table_type: table model class
        :param condition: query condition containing SQL where clause text with query parameters
        :param join_expression: SQL expression to append to FROM clause
        :param order_by: list of columns to order by, for descending order prepend column name with '-'
        :param limit: maximum number of records to return. None is no limit
        :return: list of record objects
        """
        rows = self.query_wrapper.select_many(
            table=table_type.table_name(),
            fields=table_type.fields(),
            filter_conditions=condition.filter_conditions,
            filter_params=condition.filter_params,
            join_expression=join_expression,
            order_by=order_by,
            limit=limit,
        )
        return [_convert_row_to_record_model(row, table_type) for row in rows]

    def list_all(
        self,
        table_type: Type[T],
        order_by: list[str] | None = None,
        limit: int | None = None,
    ) -> list[T]:
        """
        List all objects from a table
        :param table_type: table model class
        :param order_by: list of columns to order by, for descending order prepend column name with '-'
        :param limit: maximum number of records to return. None is no limit
        :return: list of record objects
        """
        rows = self.query_wrapper.select_many(
            table=table_type.table_name(),
            fields=table_type.fields(),
            order_by=order_by,
            limit=limit,
        )
        return [_convert_row_to_record_model(row, table_type) for row in rows]

    def count(
        self,
        table_type: Type[T],
        **filter_kwargs: Any,
    ) -> int:
        """
        Count records based on the given filter criteria
        :param table_type: table model class
        :param filter_kwargs: key-value pairs of exact filter criteria
        :return: number of records
        """
        if not filter_kwargs:
            return self.query_wrapper.count(table=table_type.table_name())

        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)
        return self.query_wrapper.count(
            table=table_type.table_name(),
            filter_conditions=filter_conditions,
            filter_params=filter_params,
        )

    def exists(
        self,
        table_type: Type[T],
        **filter_kwargs: Any,
    ) -> bool:
        """
        Check if any record exists based on the given filter criteria
        :param table_type: table model class
        :param filter_kwargs: key-value pairs of exact filter criteria
        """
        assert len(filter_kwargs), 'query should be filtered by at least one criteria'
        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)
        row = self.query_wrapper.select_one(
            table=table_type.table_name(),
            fields=[table_type.primary_key_column()],
            filter_conditions=filter_conditions,
            filter_params=filter_params,
        )
        return row is not None

    def exists_record(
        self,
        record_object: TableModel,
    ) -> bool:
        primary_key_column = record_object.primary_key_column()
        filter_kwargs = {
            primary_key_column: record_object.primary_key_value()
        }
        filter_conditions, filter_params = self._build_filter_conditions(
            type(record_object), filter_kwargs
        )
        row = self.query_wrapper.select_one(
            table=record_object.table_name(),
            fields=[primary_key_column],
            filter_conditions=filter_conditions,
            filter_params=filter_params,
        )
        return row is not None
    
    def exists_on_condition(
        self,
        table_type: Type[T],
        condition: QueryCondition,
        join_expression: str | None = None,
    ) -> bool:
        """Check if any record matches the SQL condition"""
        rows = self.query_wrapper.select_many(
            table=table_type.table_name(),
            fields=[table_type.primary_key_column()],
            join_expression=join_expression,
            filter_conditions=condition.filter_conditions,
            filter_params=condition.filter_params,
            limit=1,
        )
        return len(rows) > 0

    def create(
        self,
        record_object: TableModel,
        assign_primary_key: bool = True,
    ) -> None:
        """
        Create a new record
        :param record_object: record object to create
        :param assign_primary_key: reassign returned primary key to the original object
        """
        primary_key_column = record_object.primary_key_column()
        record_data = _extract_record_data(record_object)
        # Skip NULL primary keys, let the database auto generate them
        if primary_key_column in record_data and record_data[primary_key_column] is None:
            del record_data[primary_key_column]
        returning_row = self.query_wrapper.insert_one(
            table=record_object.table_name(),
            data=record_data,
            primary_key_columns=[primary_key_column],
        )
        if assign_primary_key:
            for primary_key, primary_value in returning_row.items():
                setattr(record_object, primary_key, primary_value)

    def update(
        self,
        record_object: TableModel,
        only_changed: bool = True,
    ) -> None:
        """
        Update one existing record
        :param record_object: record object to update
        :param only_changed: only update fields that have changed. If nothing changed, do nothing
        :raise NoRowsAffected: if the record was not found
        :raise TooManyRowsAffected: if more than one record has been updated
        """
        primary_key_column = record_object.primary_key_column()
        filter_kwargs = {
            primary_key_column: record_object.primary_key_value()
        }
        filter_conditions, filter_params = self._build_filter_conditions(
            type(record_object), filter_kwargs
        )
        if only_changed:
            update_data = _extract_changed_data(record_object)
            if not update_data:
                return
            setattr(record_object, '_original_fields', record_object.to_row())
        else:
            update_data = _extract_record_data(record_object)
        self.query_wrapper.update_one(
            table=record_object.table_name(),
            filter_conditions=filter_conditions,
            filter_params=filter_params,
            new_data=update_data,
        )

    def create_or_update(
        self,
        record_object: TableModel,
    ) -> None:
        """
        If a record already exists, update it, otherwise create it.
        """
        if self.exists_record(record_object):
            self.update(record_object, only_changed=False)
        else:
            self.create(record_object)

    def delete(
        self,
        table_type: Type[T],
        **filter_kwargs: Any,
    ) -> None:
        assert len(filter_kwargs), 'query should be filtered by at least one criteria'
        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)
        self.query_wrapper.delete_one(
            table=table_type.table_name(),
            filter_conditions=filter_conditions,
            filter_params=filter_params,
        )

    def delete_record(
        self,
        record_object: TableModel,
        cascade: bool = True,
    ) -> None:
        primary_key_column = record_object.primary_key_column()
        filter_kwargs = {
            primary_key_column: record_object.primary_key_value()
        }
        filter_conditions, filter_params = self._build_filter_conditions(
            type(record_object), filter_kwargs
        )
        if cascade:
            self._delete_cascade_dependencies(record_object)
        self.query_wrapper.delete_one(
            table=record_object.table_name(),
            filter_conditions=filter_conditions,
            filter_params=filter_params,
        )

    def _build_filter_conditions(
        self,
        table_type: Type[T],
        filter_kwargs: dict[str, Any],
    ) -> tuple[list[str], list[Any]]:
        filter_keys: list[str] = list(filter_kwargs.keys())
        fields = table_type.fields()
        for filter_key in filter_keys:
            assert filter_key in fields, f'filtered key {filter_key} is not a valid column'
        filter_conditions: list[str] = [f'{field} = {self.placeholder}' for field in filter_keys]
        filter_params = list(filter_kwargs.values())
        return filter_conditions, filter_params

    def _delete_cascade_dependencies(
        self,
        record_object: TableModel,
    ) -> None:
        origin_primary_key = record_object.primary_key_value()

        dependent_columns: dict[Type[TableModel], str] = {}
        for dependent_table in all_tables:
            on_delete_cascade = dependent_table.on_delete_cascade()
            for column, origin_table in on_delete_cascade.items():
                if origin_table is type(record_object):
                    dependent_columns[dependent_table] = column

        for dep_table, dep_column in dependent_columns.items():
            filter_kwargs = {
                dep_column: origin_primary_key
            }
            dep_records = self.find_many(dep_table, **filter_kwargs)
            for dep_record in dep_records:
                self.delete_record(dep_record, cascade=True)


def _convert_row_to_record_model(
    row: dict[str, Any],
    table_type: Type[T],
) -> T:
    valid_fields = table_type.fields()
    for column in row.keys():
        assert (
            column in valid_fields
        ), f'retrieved column "{column}" is not a valid field for the model {type(table_type)}'
    record_model = parse_typed_object(row, table_type)

    # remember original values to keep track of changed fields
    setattr(record_model, '_original_fields', record_model.to_row())
    return record_model


def _extract_record_data(record_model: TableModel) -> dict[str, Any]:
    fields: list[str] = record_model.fields()
    data = {}
    for field in fields:
        if not hasattr(record_model, field):
            raise ValueError(
                f'given table model {record_model.type_name()} has no field {field}'
            )
        data[field] = getattr(record_model, field)
    return data


def _extract_changed_data(record_model: TableModel) -> dict[str, Any]:
    originals: dict[str, Any] = getattr(record_model, '_original_fields', {})
    new_data = _extract_record_data(record_model)
    if not originals:
        logger.warning(f'could not read original fields from record {record_model.type_name()}')
        return new_data
    
    changed_data = {}
    for field, new_value in new_data.items():
        if field not in originals or new_value != originals.get(field):
            changed_data[field] = new_value
    return changed_data
