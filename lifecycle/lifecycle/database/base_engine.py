from typing import Any
from abc import ABC, abstractmethod

from lifecycle.database.base_query_builder import BaseQueryBuilder
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class DbEngine(ABC):
    def __init__(self) -> None:
        self.query_builder: BaseQueryBuilder
    
    def check_connection(self) -> None:
        pass

    def close(self):
        pass

    def get_stats(self) -> dict[str, Any]:
        return {}

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
