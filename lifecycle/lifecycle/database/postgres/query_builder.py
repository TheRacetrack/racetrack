from typing import Any, Iterable

from psycopg.sql import SQL, Literal, Identifier, Placeholder, Composable, Composed
from psycopg.abc import Query

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)

QueryWithParams = tuple[Composed, list[Any]]


class QueryBuilder:

    def select(
        self,
        table: str,
        fields: list[str],
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> QueryWithParams:
        """
        :param order_by: list of fields to order by, for descending order prepend column name with '-'
        :param filter_conditions: list of SQL conditions to include in where clause, joined with AND
        :param filter_params: list of Query parameters to place in where clause conditions
        """
        where_clause, where_params = self._build_where_clause(filter_conditions, filter_params)
        query = SQL('select {fields} from {table}{where}').format(
            fields=SQL(', ').join(map(Literal, fields)),
            table=Identifier(table),
            where=where_clause,
        )
        if limit:
            query += SQL(' limit {}').format(Literal(limit))
        if offset:
            query += SQL(' offset {}').format(Literal(offset))
        if order_by:
            order_fields = self._build_order_fields(order_by)
            query += SQL(' order by {order_fields}').format(
                order_fields=SQL(', ').join(order_fields),
            )
        return query, where_params

    def insert_one(
        self,
        table: str,
        data: dict[str, Any],
    ) -> QueryWithParams:
        query = SQL('insert into {table} ({fields}) values ({values})').format(
            table=Literal(table),
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
        query = SQL('update {table} set {updated_fields}{where}').format(
            table=Literal(table),
            updated_fields=SQL(', ').join([SQL('{} = %s').format(Identifier(field)) for field in new_data.keys()]),
            where=where_clause,
        )
        params = list(new_data.values()) + where_params
        return query, params

    def delete(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> QueryWithParams:
        where_clause, where_params = self._build_where_clause(filter_conditions, filter_params)
        query = SQL('delete from {table}{where}').format(
            table=Literal(table),
            where=where_clause,
        )
        return query, where_params
    
    def count(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> QueryWithParams:
        where_clause, where_params = self._build_where_clause(filter_conditions, filter_params)
        query = SQL('select count(*) as count from {table}{where}').format(
            table=Literal(table),
            where=where_clause,
        )
        return query, where_params
    
    def _build_where_clause(self,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> tuple[Query, list]:
        if not filter_conditions:
            return SQL(''), []
        query = SQL(' where {}').format(
            SQL(' and ').join(map(SQL, filter_conditions))
        )
        return query, filter_params or []
    
    def _build_order_fields(self, order_by: list[str] | None) -> Iterable[Composable]:
        for field in order_by or []:
            if field.startswith('-'):
                yield SQL('{} desc').format(Identifier(field[1:]))
            else:
                yield SQL('{}').format(Identifier(field))
