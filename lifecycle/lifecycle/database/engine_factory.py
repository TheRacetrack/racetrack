import os

from lifecycle.config import Config
from lifecycle.database.base_engine import DbEngine
from lifecycle.database.postgres.engine import PostgresEngine
from lifecycle.database.sqlite.engine import SQLiteEngine


def create_db_engine(config: Config) -> DbEngine:
    db_type = os.environ.get('DB_TYPE', 'postgres')
    if db_type == 'postgres':
        return PostgresEngine(max_pool_size=config.database_connection_pool, log_queries=config.database_log_queries)
    elif db_type == 'sqlite':
        return SQLiteEngine(log_queries=config.database_log_queries)
    elif db_type == 'sqlite-memory':
        return SQLiteEngine(copy=True, log_queries=config.database_log_queries)
    else:
        raise ValueError(f'Unknown database type: {db_type}')
