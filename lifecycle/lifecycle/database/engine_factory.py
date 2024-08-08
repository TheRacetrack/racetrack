import os

from lifecycle.database.engine import DbEngine
from lifecycle.database.postgres.postgres_engine import PostgresEngine
from lifecycle.database.sqlite.sqlite_engine import SQLiteEngine


def create_db_engine() -> DbEngine:
    db_type = os.environ.get('DB_TYPE', 'postgres')
    if db_type == 'postgres':
        return PostgresEngine()
    elif db_type == 'sqlite':
        return SQLiteEngine()
    else:
        raise ValueError(f'Unknown database type: {db_type}')
