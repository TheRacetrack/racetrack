from collections import defaultdict
from typing import Any, Type, TypeVar

from lifecycle.database.base_engine import DbEngine
from lifecycle.database.condition_builder import QueryCondition
from lifecycle.database.query_wrapper import QueryWrapper
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger
from lifecycle.database.table_model import TableModel, table_type_name, \
    get_primary_key_value, record_to_dict, table_metadata
from lifecycle.database.schema.tables import all_tables
from lifecycle.database.type_parser import parse_typed_object

logger = get_logger(__name__)

T = TypeVar('T', bound=TableModel)


class RecordMapper:
    def __init__(self, engine: DbEngine):
        self.query_wrapper: QueryWrapper = QueryWrapper(engine)
        self.placeholder: str = engine.query_builder.placeholder()
        self._table_name_to_class: dict[str, Type[TableModel]] = {table_metadata(cls).table_name: cls for cls in all_tables}
        self._tables_metadata: dict[Type[TableModel], TableModel.Metadata] = {cls: table_metadata(cls) for cls in all_tables}
        # cache to keep reverse dependencies for cascade delete: Origin table -> (dependant table, dependant column)
        self._delete_cascade_dependants: dict[Type[TableModel], list[tuple[Type[TableModel], str]]] = defaultdict(list)
        self._populate_delete_cascade_dependants()

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
        metadata = self._tables_metadata[table_type]
        assert len(filter_kwargs), 'query should be filtered by at least one criteria'
        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)

        row = self.query_wrapper.select_one(
            table=metadata.table_name,
            fields=metadata.fields,
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
        metadata = self._tables_metadata[table_type]
        assert len(filter_kwargs), 'query should be filtered by at least one criteria'
        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)
        rows = self.query_wrapper.select_many(
            table=metadata.table_name,
            fields=metadata.fields,
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
        :return: list of matching record objects
        """
        metadata = self._tables_metadata[table_type]
        rows = self.query_wrapper.select_many(
            table=metadata.table_name,
            fields=metadata.fields,
            filter_conditions=condition.filter_conditions,
            filter_params=condition.filter_params,
            join_expression=join_expression,
            order_by=order_by,
            limit=limit,
        )
        return [_convert_row_to_record_model(row, table_type) for row in rows]

    def filter_by_fields(
        self,
        table_type: Type[T],
        order_by: list[str] | None = None,
        offset: int | None = None,
        limit: int | None = None,
        **filter_kwargs: Any,
    ) -> list[T]:
        """
        List many records, optionally filtered by simple key-value exact fields
        :param table_type: table model class
        :param order_by: list of columns to order by, for descending order prepend column name with '-'
        :param limit: maximum number of records to return. None is no limit
        :param offset: number of records to skip from the beginning
        :return: list of matching record objects
        """
        metadata = self._tables_metadata[table_type]
        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)
        rows = self.query_wrapper.select_many(
            table=metadata.table_name,
            fields=metadata.fields,
            filter_conditions=filter_conditions,
            filter_params=filter_params,
            order_by=order_by,
            limit=limit,
            offset=offset,
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
        metadata = self._tables_metadata[table_type]
        rows = self.query_wrapper.select_many(
            table=metadata.table_name,
            fields=metadata.fields,
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
        metadata = self._tables_metadata[table_type]
        if not filter_kwargs:
            return self.query_wrapper.count(table=metadata.table_name)

        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)
        return self.query_wrapper.count(
            table=metadata.table_name,
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
        metadata = self._tables_metadata[table_type]
        assert len(filter_kwargs), 'query should be filtered by at least one criteria'
        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)
        row = self.query_wrapper.select_one(
            table=metadata.table_name,
            fields=[metadata.primary_key_column],
            filter_conditions=filter_conditions,
            filter_params=filter_params,
        )
        return row is not None

    def exists_record(
        self,
        record_object: TableModel,
    ) -> bool:
        metadata = self._tables_metadata[type(record_object)]
        filter_kwargs = {
            metadata.primary_key_column: get_primary_key_value(record_object)
        }
        filter_conditions, filter_params = self._build_filter_conditions(type(record_object), filter_kwargs)
        row = self.query_wrapper.select_one(
            table=metadata.table_name,
            fields=[metadata.primary_key_column],
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
        metadata = self._tables_metadata[table_type]
        rows = self.query_wrapper.select_many(
            table=metadata.table_name,
            fields=[metadata.primary_key_column],
            join_expression=join_expression,
            filter_conditions=condition.filter_conditions,
            filter_params=condition.filter_params,
            limit=1,
        )
        return len(rows) > 0

    def create(
        self,
        record_object: TableModel,
    ) -> None:
        """
        Create a new record
        :param record_object: record object to create
        """
        metadata = self._tables_metadata[type(record_object)]
        record_data = _extract_record_data(record_object)
        record_data = _supplement_primary_key(record_data, metadata)
        returning_row = self.query_wrapper.insert_one(
            table=metadata.table_name,
            data=record_data,
            primary_key_columns=[metadata.primary_key_column],
        )
        for primary_key, primary_value in returning_row.items():
            setattr(record_object, primary_key, primary_value)

    def create_from_dict(
        self,
        table_type: Type[T],
        record_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a new record from a dictionary of fields
        :param table_type: table model class
        :param record_data: dictionary with key-value pairs of record fields. Doesn't need to contain primary key
        :return: dictionary with record fields, including assigned primary key
        """
        metadata = self._tables_metadata[table_type]
        _validate_fields(record_data, metadata)
        record_data = _supplement_primary_key(record_data, metadata)

        returning_row = self.query_wrapper.insert_one(
            table=metadata.table_name,
            data=record_data,
            primary_key_columns=[metadata.primary_key_column],
        )
        for primary_key, primary_value in returning_row.items():
            record_data[primary_key] = primary_value
        return record_data

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
        metadata = self._tables_metadata[type(record_object)]
        filter_kwargs = {metadata.primary_key_column: get_primary_key_value(record_object)}
        filter_conditions, filter_params = self._build_filter_conditions(type(record_object), filter_kwargs)
        if only_changed:
            update_data = _extract_changed_data(record_object)
            if not update_data:
                return
            setattr(record_object, '_original_fields', record_to_dict(record_object))
        else:
            update_data = _extract_record_data(record_object)
        self.query_wrapper.update_one(
            table=metadata.table_name,
            filter_conditions=filter_conditions,
            filter_params=filter_params,
            new_data=update_data,
        )

    def update_from_dict(
        self,
        table_type: Type[T],
        primary_key_val: Any,
        update_data: dict[str, Any],
    ):
        metadata = self._tables_metadata[table_type]
        assert metadata.primary_key_column not in update_data, 'primary key should not be updated'
        _validate_fields(update_data, metadata)
        filter_kwargs = {metadata.primary_key_column: primary_key_val}
        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)
        self.query_wrapper.update_one(
            table=metadata.table_name,
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
        metadata = self._tables_metadata[table_type]
        assert len(filter_kwargs), 'query should be filtered by at least one criteria'
        filter_conditions, filter_params = self._build_filter_conditions(table_type, filter_kwargs)
        self.query_wrapper.delete_one(
            table=metadata.table_name,
            filter_conditions=filter_conditions,
            filter_params=filter_params,
        )

    def delete_record(
        self,
        record_object: TableModel,
        cascade: bool = True,
    ) -> None:
        metadata = self._tables_metadata[type(record_object)]
        filter_kwargs = {metadata.primary_key_column: get_primary_key_value(record_object)}
        filter_conditions, filter_params = self._build_filter_conditions(type(record_object), filter_kwargs)
        if cascade:
            self._delete_cascade_dependencies(record_object)
        self.query_wrapper.delete_one(
            table=metadata.table_name,
            filter_conditions=filter_conditions,
            filter_params=filter_params,
        )

    def _build_filter_conditions(
        self,
        table_type: Type[T],
        filter_kwargs: dict[str, Any],
    ) -> tuple[list[str], list[Any]]:
        metadata = self._tables_metadata[table_type]
        filter_keys: list[str] = list(filter_kwargs.keys())
        for filter_key in filter_keys:
            assert filter_key in metadata.fields, f'filtered key {filter_key} is not a valid column'
        filter_conditions: list[str] = [f'{field} = {self.placeholder}' for field in filter_keys]
        filter_params = list(filter_kwargs.values())
        return filter_conditions, filter_params

    def _delete_cascade_dependencies(
        self,
        record_object: TableModel,
    ) -> None:
        origin_primary_key = get_primary_key_value(record_object)
        dependants: list[tuple[Type[TableModel], str]] = self._delete_cascade_dependants[type(record_object)]
        for dep_table, dep_column in dependants:
            filter_kwargs = {dep_column: origin_primary_key}
            dep_records = self.find_many(dep_table, **filter_kwargs)
            for dep_record in dep_records:
                self.delete_record(dep_record, cascade=True)
                dep_record_info = f'{table_metadata(dep_record).primary_key_column} = {get_primary_key_value(dep_record)}'
                logger.debug(f'Cascade delete on record {table_type_name(dep_record)} {dep_record_info}')

    def _populate_delete_cascade_dependants(self):
        if self._delete_cascade_dependants:
            return
        for dependent_table in all_tables:
            dep_metadata = self._tables_metadata[dependent_table]
            for dep_column, origin_table in dep_metadata.on_delete_cascade.items():
                self._delete_cascade_dependants[origin_table].append((dependent_table, dep_column))

    def table_name_to_class(self, name: str) -> Type[TableModel]:
        if name not in self._table_name_to_class:
            raise EntityNotFound(f'Table class not found for table name {name}')
        return self._table_name_to_class[name]


def _convert_row_to_record_model(
    row: dict[str, Any],
    table_type: Type[T],
) -> T:
    valid_fields = table_metadata(table_type).fields
    for column in row.keys():
        assert column in valid_fields, \
            f'retrieved column "{column}" is not a valid field for the model {table_type_name(table_type)}'
    record_model = parse_typed_object(row, table_type)

    # remember original values to keep track of changed fields
    setattr(record_model, '_original_fields', record_to_dict(record_model))
    return record_model


def _extract_record_data(record_model: TableModel) -> dict[str, Any]:
    fields: list[str] = table_metadata(record_model).fields
    data = {}
    for field in fields:
        if not hasattr(record_model, field):
            raise ValueError(f'given table model {table_type_name(record_model)} has no field {field}')
        data[field] = getattr(record_model, field)
    return data


def _extract_changed_data(record_model: TableModel) -> dict[str, Any]:
    """Compare with original data and return only the fields that has been modified"""
    originals: dict[str, Any] = getattr(record_model, '_original_fields', {})
    new_data = _extract_record_data(record_model)
    if not originals:
        logger.warning(f'could not read original fields from record {table_type_name(record_model)}')
        return new_data
    
    changed_data = {}
    for field, new_value in new_data.items():
        if field not in originals or new_value != originals.get(field):
            changed_data[field] = new_value
    return changed_data


def _supplement_primary_key(record_data: dict[str, Any], metadata: TableModel.Metadata) -> dict[str, Any]:
    """Auto-generate primary key if not provided and include it in the record data"""
    primary_key_column = metadata.primary_key_column
    if not record_data.get(primary_key_column):
        id_generator = metadata.primary_key_generator
        if id_generator is not None:
            record_data[primary_key_column] = id_generator()  # generate manually if function is provided
        elif primary_key_column in record_data:
            del record_data[primary_key_column]  # let the database auto generate it
    return record_data


def _validate_fields(record_data: dict[str, Any], metadata: TableModel.Metadata):
    invalid_fields = record_data.keys() - set(metadata.fields)
    assert not invalid_fields, f'fields {sorted(invalid_fields)} are not valid columns'
