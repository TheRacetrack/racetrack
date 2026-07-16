from __future__ import annotations


class SubtractFromLastModel:
    def perform(self, numbers: list[float]) -> float:
        """
        Subtract all elements from the last element.
        :param numbers: Numbers to process (last minus all the preceding ones).
        :return: Result of subtracting all preceding elements from the last element.
        """
        if not numbers:
            return 0.0
        result = numbers[-1]
        for n in numbers[:-1]:
            result -= n
        return result

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'numbers': [10, 3, 2],
        }
