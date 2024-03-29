from typing import List


class JobEntrypoint:
    def perform(self, numbers: List[float]) -> float:
        """
        Add numbers.
        :param numbers: Numbers to add.
        :return: Sum of the numbers.
        """
        return sum(numbers)

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'numbers': [40, 2],
        }
