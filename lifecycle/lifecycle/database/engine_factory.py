import os

from lifecycle.database.base_engine import DbEngine
from lifecycle.database.postgres.engine import PostgresEngine
from lifecycle.database.sqlite.engine import SQLiteEngine


def create_db_engine() -> DbEngine:
    db_type = os.environ.get('DB_TYPE', 'postgres')
    if db_type == 'postgres':
        return PostgresEngine(log_queries=False)
    elif db_type == 'sqlite':
        return SQLiteEngine()
    elif db_type == 'sqlite-memory':
        return SQLiteEngine(copy=True)
    else:
        raise ValueError(f'Unknown database type: {db_type}')
