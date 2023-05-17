import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)


class JobEntrypoint:
    def perform(self) -> float:
        caller_name = self.get_caller_name()
        logger.info(f'perform called by {caller_name}')
        return random.random()

    def get_caller_name(self) -> Optional[str]:
        if hasattr(self, 'request_context'):
            request = getattr(self, 'request_context').get()
            return request.headers.get('X-Caller-Name')
        else:
            return None
