import os

from lifecycle.database.base_engine import DbEngine
from lifecycle.database.postgres.engine import PostgresEngine
from lifecycle.database.sqlite.engine import SQLiteEngine
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def create_db_engine() -> DbEngine:
    db_type = os.environ.get('DB_TYPE', 'postgres')
    if db_type == 'postgres':
        return PostgresEngine()
    elif db_type == 'sqlite':
        logger.info('Using local SQLite database')
        return SQLiteEngine()
    elif db_type == 'sqlite-memory':
        logger.info('Using in-memory copy of local SQLite database')
        return SQLiteEngine(copy=True)
    else:
        raise ValueError(f'Unknown database type: {db_type}')
