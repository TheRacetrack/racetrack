import random
from typing import Dict, List


class FatmanEntrypoint:
    def perform(self) -> float:
        return random.random()

    def metrics(self) -> List[Dict]:
        """Collect current metrics values"""
        return [
            {
                'name': 'fatman_wasted_seconds',
                'description': 'Seconds you have wasted here',
                'value': 1.2,
            },
            {
                'name': 'fatman_positives',
                'description': 'Number of positive results',
                'value': 5,
                'labels': {
                    'color': 'blue',
                },
            },
            {
                'name': 'fatman_zero_value',
                'description': 'Nil',
                'value': 0,
            },
            {
                'name': 'fatman_null_value',
                'description': 'Nil',
                'value': None,
            },
        ]
