import random
import os


class JobEntrypoint:
    def __init__(self):
        self.model = os.environ['TORCH_MODEL_ZOO']

    def perform(self):
        return {
            'model': self.model,
            'result': random.random(),
            'passwd': os.environ.get('PGPASSWD'),
        }
