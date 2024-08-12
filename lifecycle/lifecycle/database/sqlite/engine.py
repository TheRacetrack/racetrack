from typing import Any
import sqlite3

from racetrack_client.log.logs import get_logger
from lifecycle.database.base_engine import DbEngine, check_affected_rows
from lifecycle.database.sqlite.query_builder import QueryBuilder

logger = get_logger(__name__)

DB_PATH = 'lifecycle/django/db.sqlite3'


class SQLiteEngine(DbEngine):
    def __init__(self, copy: bool = True):
        super().__init__()
        self.connection: sqlite3.Connection
        if copy:
            src_database: sqlite3.Connection = sqlite3.connect(DB_PATH)
            self.connection = sqlite3.connect(':memory:')
            src_query = ''.join(line for line in src_database.iterdump())
            self.connection.executescript(src_query)
            src_database.close()
        else:
            self.connection = sqlite3.connect(DB_PATH)
        self.query_builder: QueryBuilder = QueryBuilder()

    def close(self):
        self.connection.close()

    def execute_sql(
        self,
        query: str,
        params: list | None = None,
        expected_affected_rows: int = -1,
    ) -> None:
        cursor: sqlite3.Cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or [])
            check_affected_rows(expected_affected_rows, cursor.rowcount)
        finally:
            cursor.close()

    def execute_sql_fetch_one(
        self, query: str, params: list | None = None
    ) -> dict[str, Any] | None:
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