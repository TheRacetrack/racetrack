from fastapi import APIRouter, Request
from pydantic import BaseModel

from lifecycle.database.table_model import table_name, table_type_name
from lifecycle.server.cache import LifecycleCache
from lifecycle.database.schema import tables
from lifecycle.auth.check import check_staff_user


class TablePayload(BaseModel):
    class_name: str
    table_name: str


class RecordGetPayload(BaseModel):
    id: str


class RecordCreatePayload(BaseModel):
    id: str


def setup_record_manager_endpoints(api: APIRouter):

    mapper = LifecycleCache.record_mapper()

    @api.get('/records/tables')
    def _get_all_tables(request: Request) -> list[TablePayload]:
        """Get list of all tables metadata"""
        check_staff_user(request)

        def retriever():
            for table_class in tables.all_tables:
                yield TablePayload(class_name=table_type_name(table_class), table_name=table_name(table_class))
        return list(retriever())

    @api.get('/records/all/{table_name}')
    def _get_all_table_records(request: Request) -> list[RecordGetPayload]:
        check_staff_user(request)
        return []

    @api.get('/records/table/{table_name}/id/{record_id}')
    def _get_one_record(request: Request, record_id: str) -> RecordGetPayload:
        check_staff_user(request)
        return RecordGetPayload(id=record_id)

    @api.post('/records/table/{table_name}')
    def _create_record(payload: RecordCreatePayload, request: Request) -> RecordGetPayload:
        """Create new ESC"""
        check_staff_user(request)
        return RecordGetPayload(id=payload.id)
