import logging
import random
from typing import Optional

logger = logging.getLogger('racetrack')


class JobEntrypoint:
    def perform(self) -> float:
        caller_name = self.get_caller_name()
        logger.debug(f'perform was called by {caller_name}')
        return random.random()

    def get_caller_name(self) -> Optional[str]:
        request = getattr(self, 'request_context').get()
        return request.headers.get('X-Caller-Name')
