import datetime
import random
from typing import Dict, List


class JobEntrypoint:
    def __init__(self):
        self._start_time = datetime.datetime.now()
        self._positives = 0

    def perform(self) -> float:
        """
        Calculate airspeed velocity of a European unladen swallow.
        :return: Random float number within [-1, 1.0) range.
        """
        number = random.random() * 2 - 1
        if number > 0:
            self._positives += 1
        return number

    def metrics(self) -> List[Dict]:
        """Collect current metrics values"""
        return [
            {
                'name': 'job_wasted_seconds',
                'description': 'Seconds you have wasted here',
                'value': self._uptime(),
            },
            {
                'name': 'job_positives',
                'description': 'Number of positive results',
                'value': self._positives,
                'labels': {
                    'color': 'blue',
                },
            },
        ]

    def _uptime(self) -> float:
        return (datetime.datetime.now() - self._start_time).seconds
