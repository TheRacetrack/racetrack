import os
from typing import Any

from psycopg_pool import ConnectionPool
from psycopg import Connection, Cursor
from psycopg.sql import SQL, Literal, Identifier, Composed

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class DbService:
    def __init__(self, max_pool_size: int = 20):
        self.connection_status: bool | None = None
        conn_params = {
            'host': os.environ.get('POSTGRES_HOST'),
            'port': os.environ.get('POSTGRES_PORT'),
            'user': os.environ.get('POSTGRES_USER'),
            'password': os.environ.get('POSTGRES_PASSWORD'),
            'dbname': get_database_name(),
        }
        self.schema = get_schema_name()

        # https://www.psycopg.org/psycopg3/docs/api/pool.html#psycopg_pool.ConnectionPool
        self.connection_pool: ConnectionPool = ConnectionPool(
            min_size=1,  # The minimum number of connection the pool will hold. The pool will actively try to create new connections if some are lost (closed, broken) and will try to never go below min_size
            max_size=max_pool_size,
            kwargs=conn_params,
            open=True,  # open the pool, creating the required connections, on init
            name='lifecycle',
            timeout=10,  # The default maximum time in seconds that a client can wait to receive a connection from the pool
            max_waiting=0,
            max_lifetime=60,  # The maximum lifetime of a connection in the pool, in seconds. Connections used for longer get closed and replaced by a new one.
            max_idle=600,  # Maximum time, in seconds, that a connection can stay unused in the pool before being closed, and the pool shrunk
            reconnect_timeout=60,  # Maximum time, in seconds, the pool will try to create a connection. If a connection attempt fails, the pool will try to reconnect a few times, using an exponential backoff and some random factor to avoid mass attempts. If repeated attempts fail, after reconnect_timeout second the connection attempt is aborted and the reconnect_failed() callback invoked
            configure=self.on_configure_connection,  # A callback to configure a connection after creation
            reconnect_failed=self.on_reconnect_failed,
            num_workers=3,  # Number of background worker threads used to maintain the pool state. Background workers are used for example to create new connections and to clean up connections when they are returned to the pool
        )

    def on_configure_connection(self, connection: Connection) -> None:
        if self.schema:
            with connection.cursor() as cursor:
                sql = SQL('SET search_path TO {schema}').format(schema=Literal(self.schema))
                cursor.execute(sql)
            connection.commit()
        self.connection_status = True

    def on_reconnect_failed(self, connection_pool: ConnectionPool) -> None:
        self.connection_status = False
        logger.error('Connection to database failed')

    def close(self):
        self.connection_pool.close()

    def get_stats(self):
        return self.connection_pool.get_stats()

    @property
    def connection_pool_size(self) -> int:
        return self.connection_pool.get_stats()['pool_size']

    def execute_sql(self, sql: Composed, params: dict | None = None) -> None:
        with self.connection_pool.connection() as conn:
            cursor: Cursor
            with conn.cursor() as cursor:
                cursor.execute(sql, params=params)

    def execute_sql_fetch_one(self, sql: Composed, params: dict | None = None) -> dict[str, Any] | None:
        with self.connection_pool.connection() as conn:
            cursor: Cursor
            with conn.cursor() as cursor:
                cursor.execute(sql, params=params)
                row = cursor.fetchone()
                if row is None:
                    return None
                col_names = [desc[0] for desc in cursor.description]
                return dict(zip(col_names, row))

    def execute_sql_fetch_all(self, sql: Composed, params: dict | None = None) -> list[dict]:
        with self.connection_pool.connection() as conn:
            cursor: Cursor
            with conn.cursor() as cursor:
                cursor.execute(sql, params=params)
                rows: list = cursor.fetchall()
                col_names = [desc[0] for desc in cursor.description]
                return [dict(zip(col_names, row)) for row in rows]

    def select_many(self, table: str) -> list[dict]:
        sql = SQL('select * from {table}').format(table=Identifier(table))
        return self.execute_sql_fetch_all(sql)


def get_database_name() -> str:
    database_name = os.environ.get('POSTGRES_DB', '')
    if '{CLUSTER_NAME}' in database_name:  # evaluate templated database name
        cluster_hostname = os.environ.get('CLUSTER_FQDN')
        assert cluster_hostname, "CLUSTER_FQDN is not set"
        parts = cluster_hostname.split('.')
        if parts[0] == os.environ.get('RACETRACK_SUBDOMAIN', 'racetrack'):
            cluster_name = parts[1]
        else:
            cluster_name = parts[0]
        database_name = database_name.replace('{CLUSTER_NAME}', cluster_name)
    return database_name


def get_schema_name() -> str | None:
    postgres_schema = os.environ.get('POSTGRES_SCHEMA', '')
    if postgres_schema == '{CLUSTER_FQDN}':
        cluster_hostname = os.environ.get('CLUSTER_FQDN')
        racetrack_subdomain = os.environ.get('RACETRACK_SUBDOMAIN', 'racetrack')
        assert cluster_hostname, "CLUSTER_FQDN is not set"
        parts = cluster_hostname.split('.')
        if parts[0] == racetrack_subdomain:
            postgres_schema = parts[1]
        else:
            postgres_schema = parts[0]

    if not postgres_schema:
        return None
    assert not postgres_schema.startswith('"'), "POSTGRES_SCHEMA should not start with '\"'"
    assert not postgres_schema.startswith("'"), "POSTGRES_SCHEMA should not start with '\''"
    return postgres_schema
