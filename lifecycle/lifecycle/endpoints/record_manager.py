from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from lifecycle.database.table_model import table_name, table_type_name, table_plural_name, table_primary_key_column, \
    TableModel, table_fields, record_to_dict, primary_key_value
from lifecycle.server.cache import LifecycleCache
from lifecycle.database.schema import tables
from lifecycle.auth.check import check_staff_user


class TableMetadataPayload(BaseModel):
    class_name: str
    table_name: str
    plural_name: str
    primary_key_column: str


class GetRecordPayload(BaseModel):
    fields: dict[str, Any]


class CreateRecordPayload(BaseModel):
    primary_key_value: str | int | None = None
    fields: dict[str, Any]


class UpdateRecordPayload(BaseModel):
    primary_key_value: str | int
    fields: dict[str, Any]


class DeleteRecordPayload(BaseModel):
    primary_key_value: str | int


class FetchManyRecordsRequest(BaseModel):
    offset: int = 0
    limit: int | None = None
    columns: list[str] | None = None
    order_by: list[str] | None = None
    filters: dict[str, Any] | None = None


class FetchManyRecordsResponse(BaseModel):
    columns: list[str]
    primary_key_column: str
    records: list[GetRecordPayload]


def setup_record_manager_endpoints(api: APIRouter):

    mapper = LifecycleCache.record_mapper()

    @api.get('/records/tables')
    def _list_all_tables(request: Request) -> list[TableMetadataPayload]:
        """Get list of metadata of all tables"""
        check_staff_user(request)

        def retriever():
            for table_class in tables.all_tables:
                yield TableMetadataPayload(
                    class_name=table_type_name(table_class),
                    table_name=table_name(table_class),
                    plural_name=table_plural_name(table_class),
                    primary_key_column=table_primary_key_column(table_class),
                )
        return list(retriever())

    @api.get('/records/count/{table}')
    def _list_table_records(request: Request, table: str) -> int:
        """Fetch many records from a table"""
        check_staff_user(request)
        table_type = mapper.table_name_to_class(table)
        return mapper.count(table_type)

    @api.post('/records/list/{table}')
    def _list_table_records(payload: FetchManyRecordsRequest, table: str, request: Request) -> FetchManyRecordsResponse:
        """Fetch many records from a table"""
        check_staff_user(request)
        table_type = mapper.table_name_to_class(table)
        filter_kwargs = payload.filters or {}
        records: list[TableModel] = mapper.filter_by_fields(
            table_type, order_by=payload.order_by, offset=payload.offset, limit=payload.limit, **filter_kwargs)
        record_payloads: list[GetRecordPayload] = [
            GetRecordPayload(fields=record_to_dict(record))
            for record in records]
        return FetchManyRecordsResponse(
            columns=table_fields(table_type),
            primary_key_column=table_primary_key_column(table_type),
            records=record_payloads,
        )

    @api.get('/records/table/{table}/id/{record_id}')
    def _get_one_record(request: Request, table: str, record_id: str) -> GetRecordPayload:
        """Get one record by ID"""
        # TODO sanitize ID input: str or int
        check_staff_user(request)
        table_type = mapper.table_name_to_class(table)
        record: TableModel = mapper.find_one(table_type, id=record_id)
        return GetRecordPayload(fields=record_to_dict(record))

    @api.post('/records/table/{table}')
    def _create_record(payload: CreateRecordPayload, table: str, request: Request) -> GetRecordPayload:
        """Create Record"""
        check_staff_user(request)
        raise NotImplementedError()

    @api.put('/records/table/{table}')
    def _update_record(payload: UpdateRecordPayload, table: str, request: Request) -> GetRecordPayload:
        """Update Record"""
        check_staff_user(request)
        raise NotImplementedError()

    @api.delete('/records/table/{table}')
    def _delete_record(payload: DeleteRecordPayload, table: str, request: Request) -> None:
        """Update Record"""
        check_staff_user(request)
        raise NotImplementedError()
