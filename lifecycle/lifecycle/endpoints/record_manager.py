from typing import Any, Iterable

from fastapi import APIRouter, Request
from pydantic import BaseModel

from lifecycle.database.record_mapper import RecordMapper
from lifecycle.database.table_model import table_type_name, TableModel, record_to_dict, table_metadata, ColumnType
from lifecycle.database.type_parser import parse_dict_typed_values
from lifecycle.server.cache import LifecycleCache
from lifecycle.database.schema import tables
from lifecycle.auth.check import check_staff_user
from racetrack_client.utils.datamodel import convert_to_json_serializable


class TableMetadataPayload(BaseModel):
    class_name: str
    table_name: str
    plural_name: str
    primary_key_column: str
    main_columns: list[str]
    all_columns: list[str]
    column_types: dict[str, ColumnType]


class RecordFieldsPayload(BaseModel):
    fields: dict[str, Any]


class FetchManyRecordsRequest(BaseModel):
    offset: int = 0
    limit: int | None = None
    order_by: list[str] | None = None
    filters: dict[str, Any] | None = None
    columns: list[str] | None = None


class FetchManyRecordsResponse(BaseModel):
    columns: list[str]
    primary_key_column: str
    records: list[RecordFieldsPayload]


class CountRecordsRequest(BaseModel):
    filters: dict[str, Any] | None = None


def setup_record_manager_endpoints(api: APIRouter):
    mapper = LifecycleCache.record_mapper()

    @api.get('/records/tables')
    def _list_all_tables_endpoint(request: Request) -> list[TableMetadataPayload]:
        """Get list of metadata for all tables"""
        check_staff_user(request)
        return list(list_all_tables())

    @api.post('/records/table/{table}')
    def _create_record_endpoint(payload: RecordFieldsPayload, table: str, request: Request) -> RecordFieldsPayload:
        """Create Record"""
        check_staff_user(request)
        return create_record(mapper, payload, table)

    @api.get('/records/table/{table}/metadata')
    def _get_table_metadata(table: str, request: Request) -> TableMetadataPayload:
        """Get metadata of a table"""
        check_staff_user(request)
        return get_table_metadata(mapper, table)

    @api.post('/records/table/{table}/count')
    def _count_table_records_endpoint(payload: CountRecordsRequest, table: str, request: Request) -> int:
        """Count how many records are in a table"""
        check_staff_user(request)
        return count_table_records(mapper, payload, table)

    @api.post('/records/table/{table}/list')
    def _list_table_records_endpoint(payload: FetchManyRecordsRequest, table: str, request: Request) -> FetchManyRecordsResponse:
        """Fetch many records from a table"""
        check_staff_user(request)
        return list_table_records(mapper, payload, table)

    @api.get('/records/table/{table}/id/{record_id}')
    def _get_one_record_endpoint(table: str, record_id: str, request: Request) -> RecordFieldsPayload:
        """Get data for one record by ID"""
        check_staff_user(request)
        return get_one_record(mapper, table, record_id)

    @api.put('/records/table/{table}/id/{record_id}')
    def _update_record_endpoint(payload: RecordFieldsPayload, table: str, record_id: str, request: Request) -> None:
        """Update fields of record selectively"""
        check_staff_user(request)
        update_record(mapper, payload, table, record_id)

    @api.delete('/records/table/{table}/id/{record_id}')
    def _delete_record_endpoint(table: str, record_id: str, request: Request) -> None:
        """Delete record by ID"""
        check_staff_user(request)
        delete_record(mapper, table, record_id)


def list_all_tables() -> Iterable[TableMetadataPayload]:
    for table_type in tables.all_tables:
        metadata = table_metadata(table_type)
        yield TableMetadataPayload(
            class_name=table_type_name(table_type),
            table_name=metadata.table_name,
            plural_name=metadata.plural_name,
            primary_key_column=metadata.primary_key_column,
            main_columns=metadata.main_columns,
            all_columns=metadata.fields,
            column_types=metadata.column_types,
        )


def get_table_metadata(mapper: RecordMapper, table: str) -> TableMetadataPayload:
    table_type = mapper.table_name_to_class(table)
    metadata = table_metadata(table_type)
    return TableMetadataPayload(
        class_name=table_type_name(table_type),
        table_name=metadata.table_name,
        plural_name=metadata.plural_name,
        primary_key_column=metadata.primary_key_column,
        main_columns=metadata.main_columns,
        all_columns=metadata.fields,
        column_types=metadata.column_types,
    )


def count_table_records(mapper: RecordMapper, payload: CountRecordsRequest, table: str) -> int:
    table_type = mapper.table_name_to_class(table)
    filters = parse_dict_typed_values(payload.filters or {}, table_type)
    return mapper.count(table_type, **filters)


def create_record(mapper: RecordMapper, payload: RecordFieldsPayload, table: str) -> RecordFieldsPayload:
    table_type = mapper.table_name_to_class(table)
    fields_data = parse_dict_typed_values(payload.fields, table_type)
    record_data = mapper.create_from_dict(table_type, fields_data)
    return RecordFieldsPayload(fields=convert_to_json_serializable(record_data))


def list_table_records(mapper: RecordMapper, payload: FetchManyRecordsRequest, table: str) -> FetchManyRecordsResponse:
    table_type = mapper.table_name_to_class(table)
    metadata = table_metadata(table_type)
    filters = parse_dict_typed_values(payload.filters or {}, table_type)
    columns = payload.columns or metadata.fields
    records: list[dict] = mapper.filter_dicts(
        table_type, columns=payload.columns,  filters=filters, order_by=payload.order_by,
        offset=payload.offset, limit=payload.limit)
    record_payloads: list[RecordFieldsPayload] = [
        RecordFieldsPayload(fields=convert_to_json_serializable(record))
        for record in records
    ]
    return FetchManyRecordsResponse(
        columns=columns,
        primary_key_column=metadata.primary_key_column,
        records=record_payloads,
    )


def get_one_record(mapper: RecordMapper, table: str, record_id: str) -> RecordFieldsPayload:
    table_type = mapper.table_name_to_class(table)
    metadata = table_metadata(table_type)
    filters = {metadata.primary_key_column: metadata.primary_key_type(record_id)}
    record: TableModel = mapper.find_one(table_type, **filters)
    return RecordFieldsPayload(fields=convert_to_json_serializable(record_to_dict(record)))


def update_record(mapper: RecordMapper, payload: RecordFieldsPayload, table: str, record_id: str) -> None:
    table_type = mapper.table_name_to_class(table)
    metadata = table_metadata(table_type)
    primary_key_type: type = metadata.primary_key_type
    primary_key_value = primary_key_type(record_id)
    fields_data = parse_dict_typed_values(payload.fields, table_type)
    mapper.update_from_dict(table_type, primary_key_value, fields_data)


def delete_record(mapper: RecordMapper, table: str, record_id: str) -> None:
    table_type = mapper.table_name_to_class(table)
    metadata = table_metadata(table_type)
    filters = {metadata.primary_key_column: metadata.primary_key_type(record_id)}
    record = mapper.find_one(table_type, **filters)
    mapper.delete_record(record, cascade=True)
