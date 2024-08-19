from functools import reduce
from typing import Any, Iterable


class QueryCondition:
    def __init__(self, expression: str, *params):
        self.expression: str = expression
        self.params: list[Any] = list(params)

    @staticmethod
    def empty() -> 'QueryCondition':
        return QueryCondition('', [])
    
    def is_empty(self) -> bool:
        return self.expression == ''

    @staticmethod
    def operator_or(*conditions: 'QueryCondition') -> 'QueryCondition':
        conditions_list = _remove_empty(conditions)
        if not conditions_list:
            return QueryCondition.empty()
        expression = ' or '.join([f'({c.expression})' for c in conditions_list])
        condition = QueryCondition(expression)
        condition.params = reduce(lambda x, y: x + y, [c.params for c in conditions_list])
        return condition

    @staticmethod
    def operator_and(*conditions: 'QueryCondition') -> 'QueryCondition':
        conditions_list = _remove_empty(conditions)
        if not conditions_list:
            return QueryCondition.empty()
        expression = ' and '.join([f'({c.expression})' for c in conditions_list])
        condition = QueryCondition(expression)
        condition.params = reduce(lambda x, y: x + y, [c.params for c in conditions_list])
        return condition

    @property
    def filter_conditions(self) -> list[str] | None:
        if self.is_empty():
            return None
        return [self.expression]
    
    @property
    def filter_params(self) -> list[Any] | None:
        return self.params if self.params else None


def _remove_empty(conditions: Iterable['QueryCondition']) -> list['QueryCondition']:
    return list(filter(lambda c: not c.is_empty(), conditions))
