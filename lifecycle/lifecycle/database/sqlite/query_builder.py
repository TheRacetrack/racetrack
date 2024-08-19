from typing import Any, Iterable

from racetrack_client.log.logs import get_logger
from lifecycle.database.base_query_builder import BaseQueryBuilder, QueryWithParams

logger = get_logger(__name__)


class QueryBuilder(BaseQueryBuilder):
    def placeholder(self) -> str:
        return '?'

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
        field_expressions: list[str]
        if join_expression:
            field_expressions = [
                f'{table}.{field} as {field}'
                for field in fields
            ]
        else:
            field_expressions = fields
        fields_joined = ', '.join(field_expressions)

        query = f'select {fields_joined} from {table}'
        if join_expression:
            query += f' {join_expression}'

        where_clause, where_params = self._build_where_clause(filter_conditions, filter_params)
        if where_clause:
            query += f' {where_clause}'
        if order_by:
            order_fields = self._build_order_fields(order_by)
            order_fields_joined = ', '.join(order_fields)
            query += f' order by {order_fields_joined}'
        if limit:
            query += f' limit {limit}'
        if offset:
            query += f' offset {offset}'
        return query, where_params

    def insert_one(
        self,
        table: str,
        data: dict[str, Any],
        primary_key_columns: list[str],
    ) -> QueryWithParams:
        fields_joined = ', '.join(data.keys())
        values_joined = ', '.join('?' * len(data))
        returning_fields = ', '.join(primary_key_columns)
        query = f'insert into {table} ({fields_joined}) values ({values_joined}) returning {returning_fields}'
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
        updated_fields = ', '.join([f'{field} = ?' for field in new_data.keys()])
        query = f'update {table} set {updated_fields}'
        if where_clause:
            query += f' {where_clause}'
        params = list(new_data.values()) + where_params
        return query, params

    def delete(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> QueryWithParams:
        where_clause, where_params = self._build_where_clause(filter_conditions, filter_params)
        query = f'delete from {table}'
        if where_clause:
            query += f' {where_clause}'
        return query, where_params

    def count(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> QueryWithParams:
        where_clause, where_params = self._build_where_clause(filter_conditions, filter_params)
        query = f'select count(*) as count from {table}'
        if where_clause:
            query += f' {where_clause}'
        return query, where_params

    def _build_where_clause(
        self,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> tuple[str | None, list]:
        if not filter_conditions:
            return None, []
        joined_conditions = ' and '.join(filter_conditions)
        query = f'where {joined_conditions}'
        return query, filter_params or []

    def _build_order_fields(self, order_by: list[str] | None) -> Iterable[str]:
        for field in order_by or []:
            if field.startswith('-'):
                yield f'{field[1:]} desc'
            else:
                yield field
