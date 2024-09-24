from __future__ import annotations


class AdderModel:
    def __init__(self):
        import time, sys
        time.sleep(10)
        sys.exit()

    def perform(self, numbers: list[float]) -> float:
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
