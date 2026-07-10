from __future__ import annotations


class MultiplierModel:
    def perform(self, numbers: list[float]) -> float:
        """
        Multiply numbers together.
        :param numbers: Numbers to multiply.
        :return: Product of the numbers.
        """
        result = 1.0
        for n in numbers:
            result *= n
        return result

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'numbers': [6, 10],
        }