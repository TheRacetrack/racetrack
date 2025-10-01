import math


class JobEntrypoint:

    def perform(self, number: int) -> bool:
        """Check if a number is prime"""
        if number < 2:
            return False
        for i in range(2, int(math.sqrt(number)) + 1):
            if number % i == 0:
                return False
        return True

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {'number': 7907}
