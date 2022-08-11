from typing import List


class AdderModel:
    def perform(self, numbers: List[float], radix: int = 10) -> float:
        """
        Add numbers.
        :param numbers: Numbers to add.
        :param radix: Radix of the numbers.
        :return: Sum of the numbers.
        """
        return sum(numbers)

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'numbers': [300, 60, 5],
            'radix': 10,
        }
