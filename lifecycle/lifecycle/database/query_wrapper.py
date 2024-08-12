from typing import Any

from lifecycle.database.base_query_builder import BaseQueryBuilder

from racetrack_client.log.logs import get_logger
from lifecycle.database.base_engine import DbEngine

logger = get_logger(__name__)


class QueryWrapper:

    def __init__(self, engine: DbEngine):
        self.engine: DbEngine = engine
        self.query_builder: BaseQueryBuilder = engine.query_builder
            
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
        query, params = self.query_builder.select(
            table=table, fields=fields,
            filter_conditions=filter_conditions, filter_params=filter_params,
            order_by=order_by,
            limit=limit, offset=offset,
        )
        return self.engine.execute_sql_fetch_all(query, params)

    def select_one(
        self,
        table: str,
        fields: list[str],
        filter_conditions: list[str],
        filter_params: list[Any],
    ) -> dict[str, Any] | None:
        query, params = self.query_builder.select(
            table=table, fields=fields,
            filter_conditions=filter_conditions, filter_params=filter_params,
            limit=1,
        )
        return self.engine.execute_sql_fetch_one(query, params)
    
    def insert_one(
        self,
        table: str,
        data: dict[str, Any],
    ) -> None:
        query, params = self.query_builder.insert_one(table=table, data=data)
        self.engine.execute_sql(query, params, expected_affected_rows=1)

    def count(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> int:
        query, params = self.query_builder.count(
            table=table,
            filter_conditions=filter_conditions, filter_params=filter_params,
        )
        row = self.engine.execute_sql_fetch_one(query, params)
        assert row is not None
        return row['count']

    def update_one(
        self,
        table: str,
        filter_conditions: list[str],
        filter_params: list[Any],
        new_data: dict[str, Any],
    ) -> None:
        query, params = self.query_builder.update(
            table=table,
            filter_conditions=filter_conditions, filter_params=filter_params,
            new_data=new_data,
        )
        self.engine.execute_sql(query, params, expected_affected_rows=1)
    
    def update_many(
        self,
        table: str,
        filter_conditions: list[str],
        filter_params: list[Any],
        new_data: dict[str, Any],
    ) -> None:
        query, params = self.query_builder.update(
            table=table,
            filter_conditions=filter_conditions, filter_params=filter_params,
            new_data=new_data,
        )
        self.engine.execute_sql(query, params)

    def delete_one(
        self,
        table: str,
        filter_conditions: list[str] | None = None,
        filter_params: list[Any] | None = None,
    ) -> None:
        query, params = self.query_builder.delete(
            table=table,
            filter_conditions=filter_conditions, filter_params=filter_params,
        )
        self.engine.execute_sql(query, params, expected_affected_rows=1)
