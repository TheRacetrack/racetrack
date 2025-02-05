import random
import os


class JobEntrypoint:
    def __init__(self):
        self.model = os.environ['TORCH_MODEL_ZOO']

    def perform(self):
        return {
            'model': self.model,
            'result': random.random(),
            'GIT_USERNAME': os.environ.get('GIT_USERNAME'),
            'GIT_TOKEN': os.environ.get('GIT_TOKEN'),
            'DEBIAN_FRONTEND': os.environ.get('DEBIAN_FRONTEND'),
            'PGPASSWD': os.environ.get('PGPASSWD'),
            'TORCH_MODEL_ZOO': os.environ.get('TORCH_MODEL_ZOO'),
        }
