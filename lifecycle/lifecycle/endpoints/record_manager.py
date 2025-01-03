from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from lifecycle.database.table_model import table_name, table_type_name, table_plural_name, table_primary_key_column
from lifecycle.server.cache import LifecycleCache
from lifecycle.database.schema import tables
from lifecycle.auth.check import check_staff_user


class TableMetadataPayload(BaseModel):
    class_name: str
    table_name: str
    plural_name: str
    primary_key_column: str


class GetRecordPayload(BaseModel):
    primary_key_value: str | int
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
    offset: int
    limit: int | None
    columns: list[str] | None = None
    order_by: list[str] | None = None
    filters: dict[str, Any] | None = None


class FetchManyRecordsResponse(BaseModel):
    total_count: int
    offset: int
    limit: int | None
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

    @api.get('/records/all/{table_name}')
    def _list_table_records(payload: FetchManyRecordsRequest, request: Request) -> FetchManyRecordsResponse:
        """Fetch many records from a table"""
        check_staff_user(request)

        table_class = mapper.get_table_class(payload.table_name)
        raise NotImplementedError()

    @api.get('/records/table/{table_name}/id/{record_id}')
    def _get_one_record(request: Request, record_id: str) -> GetRecordPayload:
        """Get one record by ID"""
        check_staff_user(request)
        raise NotImplementedError()

    @api.post('/records/table/{table_name}')
    def _create_record(payload: CreateRecordPayload, request: Request) -> GetRecordPayload:
        """Create Record"""
        check_staff_user(request)
        raise NotImplementedError()

    @api.put('/records/table/{table_name}')
    def _update_record(payload: UpdateRecordPayload, request: Request) -> GetRecordPayload:
        """Update Record"""
        check_staff_user(request)
        raise NotImplementedError()

    @api.delete('/records/table/{table_name}')
    def _delete_record(payload: DeleteRecordPayload, request: Request) -> None:
        """Update Record"""
        check_staff_user(request)
        raise NotImplementedError()
