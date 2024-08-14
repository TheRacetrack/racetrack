from typing import Any, Iterable

from psycopg.sql import SQL, Literal, Identifier, Placeholder, Composable
from psycopg.abc import Query

from racetrack_client.log.logs import get_logger
from lifecycle.database.base_query_builder import BaseQueryBuilder, QueryWithParams

logger = get_logger(__name__)


class QueryBuilder(BaseQueryBuilder):
    def placeholder(self) -> str:
        return '%s'

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
        """
        field_expressions: list[Composable]
        if join_expression:
            field_expressions = [
                SQL('{}.{} as {}').format(Identifier(table), Identifier(field), Identifier(field))
                for field in fields
            ]
        else:
            field_expressions = [Identifier(field) for field in fields]

        query = SQL('select {fields} from {table}').format(
            fields=SQL(', ').join(field_expressions),
            table=Identifier(table),
        )
        if join_expression:
            query += SQL(' ' + join_expression)

        where_clause, where_params = self._build_where_clause(filter_conditions, filter_params)
        if where_clause:
            query += SQL(' {}').format(where_clause)
        if order_by:
            order_fields = self._build_order_fields(order_by)
            query += SQL(' order by {order_fields}').format(
                order_fields=SQL(', ').join(order_fields),
            )
        if limit:
            query += SQL(' limit {}').format(Literal(limit))
        if offset:
            query += SQL(' offset {}').format(Literal(offset))
        return query, where_params

    def insert_one(
        self,
        table: str,
        data: dict[str, Any],
    ) -> QueryWithParams:
        query = SQL('insert into {table} ({fields}) values ({values})').format(
            table=Identifier(table),
            fields=SQL(', ').join(map(Identifier, data.keys())),
            values=SQL(', ').join(Placeholder() * len(data)),
        )
        params = list(data.values())
        return query, params

    def update(
        self,
        table: str,
        new_data: dict[str, Any],
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> QueryWithParams:
        where_clause, where_params = self._build_where_clause(filter_conditions, filter_params)
        query = SQL('update {table} set {updated_fields}').format(
            table=Identifier(table),
            updated_fields=SQL(', ').join(
                [SQL('{} = %s').format(Identifier(field)) for field in new_data.keys()]
            ),
        )
        if where_clause:
            query += SQL(' {}').format(where_clause)
        params = list(new_data.values()) + where_params
        return query, params

    def delete(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> QueryWithParams:
        where_clause, where_params = self._build_where_clause(filter_conditions, filter_params)
        query = SQL('delete from {table}').format(
            table=Identifier(table),
        )
        if where_clause:
            query += SQL(' {}').format(where_clause)
        return query, where_params

    def count(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> QueryWithParams:
        where_clause, where_params = self._build_where_clause(filter_conditions, filter_params)
        query = SQL('select count(*) as count from {table}').format(
            table=Identifier(table),
        )
        if where_clause:
            query += SQL(' {}').format(where_clause)
        return query, where_params

    def _build_where_clause(
        self,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> tuple[Query | None, list]:
        if not filter_conditions:
            return None, []
        query = SQL('where {}').format(
            SQL(' and ').join(map(SQL, filter_conditions))  # type: ignore
        )
        return query, filter_params or []

    def _build_order_fields(self, order_by: list[str] | None) -> Iterable[Composable]:
        for field in order_by or []:
            if field.startswith('-'):
                yield SQL('{} desc').format(Identifier(field[1:]))
            else:
                yield SQL('{}').format(Identifier(field))
