from __future__ import annotations


class SubtractAllModel:
    def perform(self, numbers: list[float]) -> float:
        """
        Subtract all numbers from zero.
        :param numbers: Numbers to subtract from zero.
        :return: Result of subtracting all numbers from zero (i.e. negated sum).
        """
        result = 0.0
        for n in numbers:
            result -= n
        return result

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'numbers': [10, 3],
        }
