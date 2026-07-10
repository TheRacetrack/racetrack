from __future__ import annotations


class SubtractorModel:
    def perform(self, numbers: list[float]) -> float:
        """
        Subtract numbers sequentially.
        :param numbers: Numbers to subtract (first minus the rest).
        :return: Result of sequential subtraction.
        """
        if not numbers:
            return 0.0
        result = numbers[0]
        for n in numbers[1:]:
            result -= n
        return result

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'numbers': [10, 3],
        }