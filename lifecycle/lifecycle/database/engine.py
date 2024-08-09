from typing import Any
from abc import ABC, abstractmethod

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class DbEngine(ABC):

    def close(self):
        pass

    def get_stats(self) -> dict[str, Any]:
        return {}

    @abstractmethod
    def execute_sql(
        self,
        query: str,
        params: list | None = None,
        expected_affected_rows: int = -1,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def execute_sql_fetch_one(self, query: str, params: list | None = None) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def execute_sql_fetch_all(self, query: str, params: list | None = None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def placeholder(self) -> str:
        return '?'
    
    @abstractmethod
    def select_many(
        self,
        table: str,
        fields: list[str],
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def select_one(
        self,
        table: str,
        fields: list[str],
        filter_conditions: list[str],
        filter_params: list[Any],
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def insert_one(
        self,
        table: str,
        data: dict[str, Any],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def count(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> int:
        raise NotImplementedError
    
    @abstractmethod
    def update_many(
        self,
        table: str,
        filter_conditions: list[str],
        filter_params: list[Any],
        new_data: dict[str, Any],
    ) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def update_one(
        self,
        table: str,
        filter_conditions: list[str],
        filter_params: list[Any],
        new_data: dict[str, Any],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_one(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> None:
        raise NotImplementedError


class NoRowsAffected(RuntimeError):
    pass

class TooManyRowsAffected(RuntimeError):
    pass


def _check_affected_rows(expected: int, actual: int):
    if expected > 0:
        if actual > expected:
            raise TooManyRowsAffected(f'Affected too many rows: {actual}, expected {expected}')
        elif actual == 0:
            raise NoRowsAffected(f'No rows affected, expected {expected}')
        elif actual != expected:
            raise RuntimeError(f'Expected {expected} rows affected, but got {actual}')
