from datetime import datetime
from typing import Any
import sqlite3
import os

from racetrack_client.log.errors import AlreadyExists
from racetrack_client.log.logs import get_logger
from lifecycle.database.base_engine import DbEngine, check_affected_rows
from lifecycle.database.sqlite.query_builder import QueryBuilder

logger = get_logger(__name__)

DB_PATH: str = os.environ.get('DB_PATH', 'lifecycle/django/db.sqlite3')


class SQLiteEngine(DbEngine):
    def __init__(self, copy: bool = True, log_queries: bool = True) -> None:
        super().__init__()
        if copy:
            logger.info(f'Using in-memory copy of local SQLite database: {DB_PATH}')
        else:
            logger.info(f'Using local SQLite database: {DB_PATH}')

        self.connection: sqlite3.Connection
        if copy:
            src_database: sqlite3.Connection = sqlite3.connect(DB_PATH)
            self.connection = sqlite3.connect(':memory:', check_same_thread=False)
            src_query = ''.join(line for line in src_database.iterdump())
            self.connection.executescript(src_query)
            src_database.close()
        else:
            self.connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.query_builder: QueryBuilder = QueryBuilder()
        self.log_queries: bool = log_queries

        sqlite3.register_adapter(datetime, _adapt_datetime)

    def check_connection(self) -> None:
        self.connection.execute('select 1')

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
            self._log_query(query)
            try:
                cursor.execute(query, params or [])
            except sqlite3.IntegrityError as e:
                raise AlreadyExists(str(e)) from e
            check_affected_rows(expected_affected_rows, cursor.rowcount)
        finally:
            cursor.close()

    def execute_sql_fetch_one(
        self,
        query: str,
        params: list | None = None,
    ) -> dict[str, Any] | None:
        cursor: sqlite3.Cursor = self.connection.cursor()
        try:
            self._log_query(query)
            try:
                cursor.execute(query, params or [])
            except sqlite3.IntegrityError as e:
                raise AlreadyExists(str(e)) from e
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
            self._log_query(query)
            cursor.execute(query, params or [])
            rows: list = cursor.fetchall()
            assert cursor.description, 'no column names in the result'
            col_names = [desc[0] for desc in cursor.description]
            return [dict(zip(col_names, row)) for row in rows]
        finally:
            cursor.close()

    def _log_query(self, query: str) -> None:
        if self.log_queries:
            logger.debug(f'SQL query: {query}')


def _adapt_datetime(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
