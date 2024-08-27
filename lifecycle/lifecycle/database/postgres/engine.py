import os
from typing import Any

from psycopg_pool import ConnectionPool, PoolTimeout
from psycopg import Connection, Cursor, DatabaseError, IntegrityError, InterfaceError
from psycopg.sql import SQL, Literal, Composable, Composed

from lifecycle.server.metrics import metric_database_connection_failed, metric_database_connection_opened, \
    metric_database_connection_closed, metric_database_queries_executed
from racetrack_client.log.context_error import ContextError
from racetrack_client.log.errors import AlreadyExists
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from lifecycle.database.base_engine import DbEngine, check_affected_rows, DatabaseStatus
from lifecycle.database.postgres.query_builder import QueryBuilder
from racetrack_client.utils.shell import shell, CommandError

logger = get_logger(__name__)


class PostgresEngine(DbEngine):
    def __init__(self, max_pool_size: int, log_queries: bool):
        super().__init__()
        conn_params = get_connection_params()
        self.connection_status: bool | None = None
        self.schema: str | None = _get_schema_name()
        self.log_queries: bool = log_queries
        self.query_builder: QueryBuilder = QueryBuilder()
        self._database_status: DatabaseStatus = DatabaseStatus()
        # https://www.psycopg.org/psycopg3/docs/api/pool.html#psycopg_pool.ConnectionPool
        self.connection_pool: ConnectionPool = ConnectionPool(
            connection_class=PgConnection,
            kwargs=conn_params,
            min_size=1,  # The minimum number of connection the pool will hold. The pool will actively try to create new connections if some are lost (closed, broken) and will try to never go below min_size
            max_size=max_pool_size,  # The maximum number of connections the pool will hold
            open=True,  # open the pool, creating the required connections, on init
            configure=self._on_configure_connection,  # A callback to configure a connection after creation
            check=None,  # A callback to check that a connection is working correctly when obtained by the pool.
            reset=self._on_reset_connection,  # A callback to reset a function after it has been returned to the pool
            name='lifecycle',  # name to give to the pool, useful, for instance, to identify it in the logs
            timeout=5,  # The default maximum time in seconds that a client can wait to receive a connection from the pool
            max_waiting=0,  # Maximum number of requests that can be queued to the pool, after which new requests will fail, raising TooManyRequests. 0 means no queue limit.
            max_lifetime=10*60,  # The maximum lifetime of a connection in the pool, in seconds. Connections used for longer get closed and replaced by a new one.
            max_idle=60,  # Maximum time, in seconds, that a connection can stay unused in the pool before being closed, and the pool shrunk
            reconnect_timeout=5,  # Maximum time, in seconds, the pool will try to create a connection. If a connection attempt fails, the pool will try to reconnect a few times, using an exponential backoff and some random factor to avoid mass attempts. If repeated attempts fail, after reconnect_timeout second the connection attempt is aborted and the reconnect_failed() callback invoked
            reconnect_failed=self._on_reconnect_failed,  # Callback invoked if an attempt to create a new connection fails for more than reconnect_timeout seconds
            num_workers=3,  # Number of background worker threads used to maintain the pool state. Background workers are used for example to create new connections and to clean up connections when they are returned to the pool
        )

    def _on_configure_connection(self, connection: Connection) -> None:
        if self.schema:
            with connection.cursor() as cursor:
                query = SQL('SET search_path TO {schema}').format(schema=Literal(self.schema))
                cursor.execute(query)
            connection.commit()
        metric_database_connection_opened.inc()
        self.connection_status = True

    def _on_reconnect_failed(self, _: ConnectionPool) -> None:
        self.connection_status = False
        metric_database_connection_failed.inc()
        logger.error('Failed to reconnect to database')

    def _on_reset_connection(self, _: Connection) -> None:
        metric_database_connection_closed.inc()
    
    def check_connection(self) -> None:
        try:
            conn_params = get_connection_params()
            dbname = conn_params['dbname']
            user = conn_params['user']
            host = conn_params['host']
            port = conn_params['port']
            shell(f'pg_isready -h {host} -p {port} -U {user} -d {dbname}', print_stdout=False, print_log=False)
        except CommandError as e:
            self._database_status.connected = False
            metric_database_connection_failed.inc()
            raise ContextError('Connection to database failed (pg_isready failed)') from e

        try:
            self.connection_pool.check()
        except BaseException as e:
            self._database_status.connected = False
            metric_database_connection_failed.inc()
            raise ContextError('Connection pool check failed') from e

        try:
            self.execute_sql('select 1')
        except BaseException as e:
            self._database_status.connected = False
            raise ContextError('Test query failed') from e

        self._database_status.connected = True

    def close(self):
        self.connection_pool.close()
        self._database_status.connected = False

    def database_status(self) -> DatabaseStatus:
        # https://www.psycopg.org/psycopg3/docs/advanced/pool.html#pool-stats
        stats: dict[str, int] = self.connection_pool.get_stats()
        self._database_status.pool_size = stats.get('pool_size', 0)
        self._database_status.pool_available = stats.get('pool_available', 0)
        self._database_status.requests_waiting = stats.get('requests_waiting', 0)
        self._database_status.usage_ms = stats.get('usage_ms', 0)
        self._database_status.requests_num = stats.get('requests_num', 0)
        self._database_status.requests_queued = stats.get('requests_queued', 0)
        self._database_status.requests_wait_ms = stats.get('requests_wait_ms', 0)
        self._database_status.requests_errors = stats.get('requests_errors', 0)
        self._database_status.connections_num = stats.get('connections_num', 0)
        self._database_status.connections_ms = stats.get('connections_ms', 0)
        self._database_status.connections_errors = stats.get('connections_errors', 0)
        return self._database_status

    def execute_sql(
        self,
        query: str | Composed,
        params: list | None = None,
        expected_affected_rows: int = -1,
    ) -> None:
        try:
            with self.connection_pool.connection() as conn:
                cursor: Cursor
                with conn.cursor() as cursor:
                    sql = self._get_query_bytes(query, conn)
                    self._log_query(sql)
                    cursor.execute(sql, params=params)
                    metric_database_queries_executed.inc()
                    check_affected_rows(expected_affected_rows, cursor.rowcount)
        except IntegrityError as e:
            raise AlreadyExists(str(e)) from e
        except PoolTimeout as e:
            metric_database_connection_failed.inc()
            raise ContextError(f'Database connection pool error: {type(e).__name__}') from e
        except DatabaseError as e:
            raise ContextError(f'Database error: {type(e).__name__}') from e
        except InterfaceError as e:
            raise ContextError(f'Database interface error: {type(e).__name__}') from e

    def execute_sql_fetch_one(
        self,
        query: str | Composed,
        params: list | None = None,
    ) -> dict[str, Any] | None:
        try:
            with self.connection_pool.connection() as conn:
                cursor: Cursor
                with conn.cursor() as cursor:
                    sql = self._get_query_bytes(query, conn)
                    self._log_query(sql)
                    cursor.execute(sql, params=params)
                    metric_database_queries_executed.inc()
                    row = cursor.fetchone()
                    if row is None:
                        return None
                    assert cursor.description, 'no column names in the result'
                    col_names = [desc[0] for desc in cursor.description]
                    return dict(zip(col_names, row))
        except IntegrityError as e:
            raise AlreadyExists(str(e)) from e
        except PoolTimeout as e:
            metric_database_connection_failed.inc()
            raise ContextError(f'Database connection pool error: {type(e).__name__}') from e
        except DatabaseError as e:
            raise ContextError(f'Database error: {type(e).__name__}') from e
        except InterfaceError as e:
            raise ContextError(f'Database interface error: {type(e).__name__}') from e

    def execute_sql_fetch_all(
        self, query: str | Composed, params: list | None = None
    ) -> list[dict]:
        try:
            with self.connection_pool.connection() as conn:
                cursor: Cursor
                with conn.cursor() as cursor:
                    sql = self._get_query_bytes(query, conn)
                    self._log_query(sql)
                    cursor.execute(sql, params=params)
                    metric_database_queries_executed.inc()
                    rows: list = cursor.fetchall()
                    assert cursor.description, 'no column names in the result'
                    col_names = [desc[0] for desc in cursor.description]
                    return [dict(zip(col_names, row)) for row in rows]
        except IntegrityError as e:
            raise AlreadyExists(str(e)) from e
        except PoolTimeout as e:
            metric_database_connection_failed.inc()
            raise ContextError(f'Database connection pool error: {type(e).__name__}') from e
        except DatabaseError as e:
            raise ContextError(f'Database error: {type(e).__name__}') from e
        except InterfaceError as e:
            raise ContextError(f'Database interface error: {type(e).__name__}') from e

    def _get_query_bytes(self, query: str | Composed, connection: Connection) -> bytes:
        if isinstance(query, Composable):
            return query.as_bytes(connection)
        if isinstance(query, str):
            return query.encode()

    def _log_query(self, query: bytes) -> None:
        if self.log_queries:
            logger.debug(f'SQL query: {query.decode()}')


class PgConnection(Connection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def connect(cls, *args, **kwargs) -> "Connection":
        try:
            return Connection.connect(*args, **kwargs)
        except BaseException as e:
            metric_database_connection_failed.inc()
            log_exception(ContextError('Connection to database failed', e))
            raise


def get_connection_params() -> dict[str, str]:
    database_name = os.environ.get('POSTGRES_DB', '')
    database_name = _evaluate_cluster_name(database_name)
    params = {
        'host': os.environ.get('POSTGRES_HOST'),
        'port': os.environ.get('POSTGRES_PORT'),
        'user': os.environ.get('POSTGRES_USER'),
        'password': os.environ.get('POSTGRES_PASSWORD'),
        'dbname': database_name,
        'sslmode': os.environ.get('POSTGRES_SSLMODE'),
        'sslrootcert': os.environ.get('POSTGRES_SSLROOTCERT'),
    }
    return {k: v for k, v in params.items() if v is not None}


def _get_schema_name() -> str | None:
    postgres_schema = os.environ.get('POSTGRES_SCHEMA', '')
    postgres_schema = _evaluate_cluster_name(postgres_schema)
    if not postgres_schema:
        return None
    assert not postgres_schema.startswith('"'), "POSTGRES_SCHEMA should not start with '\"'"
    assert not postgres_schema.startswith("'"), "POSTGRES_SCHEMA should not start with '''"
    return postgres_schema


def _evaluate_cluster_name(name: str) -> str:
    if '{CLUSTER_NAME}' not in name:
        return name
    cluster_hostname = os.environ.get('CLUSTER_FQDN')
    assert cluster_hostname, 'CLUSTER_FQDN is not set'
    cluster_parts = cluster_hostname.split('.')
    racetrack_subdomain = os.environ.get('RACETRACK_SUBDOMAIN', 'racetrack')
    if cluster_parts[0] == racetrack_subdomain:
        cluster_name = cluster_parts[1]
    else:
        cluster_name = cluster_parts[0]
    return name.replace('{CLUSTER_NAME}', cluster_name)
