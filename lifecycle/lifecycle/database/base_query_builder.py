from typing import Any
from abc import ABC, abstractmethod

from psycopg.sql import Composed

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)

QueryWithParams = tuple[str | Composed, list[Any]]


class BaseQueryBuilder(ABC):
    @abstractmethod
    def placeholder(self) -> str:
        """Placeholder for query parameters"""
        return '?'

    @abstractmethod
    def select(
        self,
        table: str,
        fields: list[str],
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
        join_expression: str | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> QueryWithParams:
        """
        :param order_by: list of fields to order by, for descending order prepend column name with '-'
        :param filter_conditions: list of SQL conditions to include in where clause, joined with AND
        :param filter_params: list of Query parameters to place in where clause conditions
        :param join_expression: expression to join tables in SQL query, eg. 'left join table2 on table1.id = table2.id'
        """
        raise NotImplementedError

    @abstractmethod
    def insert_one(
        self,
        table: str,
        data: dict[str, Any],
    ) -> QueryWithParams:
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        table: str,
        new_data: dict[str, Any],
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> QueryWithParams:
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> QueryWithParams:
        raise NotImplementedError

    @abstractmethod
    def count(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> QueryWithParams:
        raise NotImplementedError
