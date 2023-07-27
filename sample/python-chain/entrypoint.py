from typing import List

from job_wrapper.call import call_job


class JobEntrypoint:
    def perform(self, numbers: List[float]) -> float:
        """Round result from another model"""
        partial = call_job(self, 'adder', '/api/v1/perform', {'numbers': numbers})
        return round(partial)

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'numbers': [0.2, 0.9],
        }
