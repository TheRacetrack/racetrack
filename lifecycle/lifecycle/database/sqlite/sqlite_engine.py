from typing import Any
import sqlite3

from racetrack_client.log.logs import get_logger
from lifecycle.database.engine import DbEngine, _check_affected_rows
from lifecycle.database.sqlite.query_builder import QueryBuilder

logger = get_logger(__name__)


class SQLiteEngine(DbEngine):

    def __init__(self, copy: bool = True):
        super().__init__()
        self.connection: sqlite3.Connection
        if copy:
            src_database: sqlite3.Connection = sqlite3.connect("lifecycle/django/db.sqlite3")
            self.connection = sqlite3.connect(':memory:')
            src_query = "".join(line for line in src_database.iterdump())
            self.connection.executescript(src_query)
            src_database.close()
        else:
            self.connection = sqlite3.connect("lifecycle/django/db.sqlite3")
        self.query_builder: QueryBuilder = QueryBuilder()

    def close(self):
        self.connection.close()

    def placeholder(self) -> str:
        return '?'

    def execute_sql(
        self,
        query: str,
        params: list | None = None,
        expected_affected_rows: int = -1,
    ) -> None:
        cursor: sqlite3.Cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or [])
            _check_affected_rows(expected_affected_rows, cursor.rowcount)
        finally:
            cursor.close()

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
        filter_conditions: list[str],
        filter_params: list[Any],
    ) -> dict[str, Any] | None:
        query, params = self.query_builder.select(
            table=table, fields=fields,
            filter_conditions=filter_conditions, filter_params=filter_params,
            limit=1,
        )
        return self.execute_sql_fetch_one(query, params)
    
    def insert_one(
        self,
        table: str,
        data: dict[str, Any],
    ) -> None:
        query, params = self.query_builder.insert_one(table=table, data=data)
        self.execute_sql(query, params, expected_affected_rows=1)

    def count(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> int:
        query, params = self.query_builder.count(
            table=table,
            filter_conditions=filter_conditions, filter_params=filter_params,
        )
        row = self.execute_sql_fetch_one(query, params)
        assert row is not None
        return row['count']
    
    def update_one(
        self,
        table: str,
        filter_conditions: list[str],
        filter_params: list[Any],
        new_data: dict[str, Any],
    ) -> None:
        query, params = self.query_builder.update(
            table=table,
            filter_conditions=filter_conditions, filter_params=filter_params,
            new_data=new_data,
        )
        self.execute_sql(query, params, expected_affected_rows=1)
    
    def update_many(
        self,
        table: str,
        filter_conditions: list[str],
        filter_params: list[Any],
        new_data: dict[str, Any],
    ) -> None:
        query, params = self.query_builder.update(
            table=table,
            filter_conditions=filter_conditions, filter_params=filter_params,
            new_data=new_data,
        )
        self.execute_sql(query, params)

    def delete_one(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> None:
        query, params = self.query_builder.delete(
            table=table,
            filter_conditions=filter_conditions, filter_params=filter_params,
        )
        self.execute_sql(query, params, expected_affected_rows=1)
