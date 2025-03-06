from typing import Any, Iterable, Type

from fastapi import APIRouter, Request
from pydantic import BaseModel

from lifecycle.database.record_mapper import RecordMapper
from lifecycle.database.table_model import table_type_name, TableModel, record_to_dict, table_metadata, ColumnType
from lifecycle.database.type_parser import parse_dict_typed_values
from lifecycle.server.cache import LifecycleCache
from lifecycle.database.schema import tables
from lifecycle.auth.check import check_staff_user
from racetrack_client.utils.datamodel import convert_to_json_serializable
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class TableMetadataPayload(BaseModel):
    class_name: str
    table_name: str
    plural_name: str
    primary_key_column: str
    main_columns: list[str]
    all_columns: list[str]
    column_types: dict[str, ColumnType]
    foreign_keys: dict[str, str]  # column name -> foreign table name


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


class ManyRecordsRequest(BaseModel):
    record_ids: list[str]


class FetchManyNamesResponse(BaseModel):
    id_to_name: dict[str, str]


def setup_records_endpoints(api: APIRouter):
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

    @api.post('/records/table/{table}/names')
    def _enrich_record_names(payload: ManyRecordsRequest, table: str, request: Request) -> FetchManyNamesResponse:
        """Enrich record IDs with their names"""
        check_staff_user(request)
        return enrich_record_names(mapper, payload, table)

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

    @api.delete('/records/table/{table}/many')
    def _delete_many_records_endpoint(payload: ManyRecordsRequest, table: str, request: Request) -> None:
        """Delete multiple records by ID"""
        check_staff_user(request)
        delete_many_records(mapper, table, payload.record_ids)


def list_all_tables() -> Iterable[TableMetadataPayload]:
    for table_type in tables.all_tables:
        yield _build_table_metadata_payload(table_type)


def get_table_metadata(mapper: RecordMapper, table: str) -> TableMetadataPayload:
    table_type = mapper.table_name_to_class(table)
    return _build_table_metadata_payload(table_type)


def _build_table_metadata_payload(table_type: Type[TableModel]) -> TableMetadataPayload:
    metadata = table_metadata(table_type)
    foreign_keys = {}
    for column_name, foreign_type in metadata.on_delete_cascade.items():
        foreign_keys[column_name] = table_metadata(foreign_type).table_name
    return TableMetadataPayload(
        class_name=table_type_name(table_type),
        table_name=metadata.table_name,
        plural_name=metadata.plural_name,
        primary_key_column=metadata.primary_key_column,
        main_columns=metadata.main_columns,
        all_columns=metadata.fields,
        column_types=metadata.column_types,
        foreign_keys=foreign_keys,
    )


def count_table_records(mapper: RecordMapper, payload: CountRecordsRequest, table: str) -> int:
    table_type = mapper.table_name_to_class(table)
    filters = parse_dict_typed_values(payload.filters or {}, table_type)
    return mapper.count(table_type, **filters)


def create_record(mapper: RecordMapper, payload: RecordFieldsPayload, table: str) -> RecordFieldsPayload:
    table_type = mapper.table_name_to_class(table)
    fields_data = parse_dict_typed_values(payload.fields, table_type)
    record_data = mapper.create_from_dict(table_type, fields_data)
    logger.info(f'New record created in table {table}')
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


def enrich_record_names(mapper: RecordMapper, payload: ManyRecordsRequest, table: str) -> FetchManyNamesResponse:
    table_type = mapper.table_name_to_class(table)
    id_to_name: dict[str, str] = {}
    for record_id in set(payload.record_ids):
        if record_id:
            record_name = mapper.get_record_name(table_type, record_id)
            if record_name is not None:
                id_to_name[record_id] = record_name
    return FetchManyNamesResponse(id_to_name=id_to_name)


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
    logger.info(f'Record {record_id} deleted from table {table}')


def delete_many_records(mapper: RecordMapper, table: str, record_ids: list[str]) -> None:
    table_type = mapper.table_name_to_class(table)
    metadata = table_metadata(table_type)
    primary_keys = [metadata.primary_key_type(record_id) for record_id in record_ids]
    for primary_key in primary_keys:
        filters = {metadata.primary_key_column: primary_key}
        record = mapper.find_one(table_type, **filters)
        mapper.delete_record(record, cascade=True)
    logger.info(f'Records {record_ids} deleted from table {table}')
