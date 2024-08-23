from dataclasses import dataclass
from typing import Any
from abc import ABC, abstractmethod

from lifecycle.database.base_query_builder import BaseQueryBuilder
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


@dataclass
class DatabaseStatus:
    connected: bool | None = None
    pool_size: int = 0  # Number of connections currently managed by the pool (in the pool, given to clients, being prepared)
    pool_available: int = 0  # Number of connections currently idle in the pool
    requests_waiting: int = 0  # Number of requests currently waiting in a queue to receive a connection
    usage_ms: float = 0  # Total usage time of the connections outside the pool
    requests_num: int = 0  # Number of connections requested to the pool
    requests_queued: int = 0  # Number of requests queued because a connection wasn’t immediately available in the pool
    requests_wait_ms: float = 0  # Total time in the queue for the clients waiting
    requests_errors: int = 0  # Number of connection requests resulting in an error (timeouts, queue full)
    connections_num: int = 0  # Number of connection attempts made by the pool to the server
    connections_ms: float = 0  # Total time spent to establish connections with the server
    connections_errors: int = 0  # Number of failed connection attempts


class DbEngine(ABC):
    def __init__(self) -> None:
        self.query_builder: BaseQueryBuilder
    
    def check_connection(self) -> None:
        pass

    def close(self):
        pass

    @abstractmethod
    def database_status(self) -> DatabaseStatus:
        raise NotImplementedError

    @abstractmethod
    def execute_sql(
        self,
        query,
        params: list | None = None,
        expected_affected_rows: int = -1,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def execute_sql_fetch_one(
        self,
        query,
        params: list | None = None,
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def execute_sql_fetch_all(
        self,
        query,
        params: list | None = None,
    ) -> list[dict]:
        raise NotImplementedError

    def last_query(self) -> str | None:
        return None


class NoRowsAffected(RuntimeError):
    pass


class TooManyRowsAffected(RuntimeError):
    pass


def check_affected_rows(expected: int, actual: int):
    if expected > 0:
        if actual > expected:
            raise TooManyRowsAffected(f'Affected too many rows: {actual}, expected {expected}')
        elif actual == 0:
            raise NoRowsAffected(f'No rows affected, expected {expected}')
        elif actual != expected:
            raise RuntimeError(f'Expected {expected} rows affected, but got {actual}')
