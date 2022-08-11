# mypy: ignore-errors
from typing import List


class BadEntrypoint:
    def perform(self, numbers: List[float], radix: int = 10) -> float:
        return syntax error  # noqa: E999
