from typing import Any
import sqlite3

from racetrack_client.log.logs import get_logger
from lifecycle.database.engine import DbEngine
from lifecycle.database.sqlite.query_builder import QueryBuilder

logger = get_logger(__name__)


class SQLiteEngine(DbEngine):

    def __init__(self):
        super().__init__()
        self.connection: sqlite3.Connection = sqlite3.connect("lifecycle/django/db.sqlite3")
        self.query_builder: QueryBuilder = QueryBuilder()

    def close(self):
        self.connection.close()

    def placeholder(self) -> str:
        return '?'

    def execute_sql(self, query: str, params: list | None = None) -> None:
        self.connection.execute(query, params or [])

    def execute_sql_fetch_one(self, query: str, params: list | None = None) -> dict[str, Any] | None:
        cursor: sqlite3.Cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or [])
            row = cursor.fetchone()
            if row is None:
                return None
            assert cursor.description, 'no column names in the result'
            col_names = [desc[0] for desc in cursor.description]
            return dict(zip(col_names, row))
        finally:
            cursor.close()

    def execute_sql_fetch_all(self, query: str, params: list | None = None) -> list[dict]:
        cursor: sqlite3.Cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or [])
            rows: list = cursor.fetchall()
            assert cursor.description, 'no column names in the result'
            col_names = [desc[0] for desc in cursor.description]
            return [dict(zip(col_names, row)) for row in rows]
        finally:
            cursor.close()
 
    def select_many(
        self,
        table: str,
        fields: list[str],
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        query, params = self.query_builder.select(
            table=table, fields=fields,
            filter_conditions=filter_conditions, filter_params=filter_params,
            order_by=order_by,
            limit=limit, offset=offset,
        )
        return self.execute_sql_fetch_all(query, params)

    def select_one(
        self,
        table: str,
        fields: list[str],
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> dict[str, Any] | None:
        query, params = self.query_builder.select(
            table=table, fields=fields,
            filter_conditions=filter_conditions, filter_params=filter_params,
            limit=1,
        )
        return self.execute_sql_fetch_one(query, params)
