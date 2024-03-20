from datetime import timedelta

from racetrack_client.utils.time import now
from racetrack_client.log.logs import get_logger
from lifecycle.config import Config
from lifecycle.django.registry import models

logger = get_logger(__name__)


def clean_up_async_job_calls(config: Config):
    older_than = now() - timedelta(seconds=config.async_job_call_lifetime)
    queryset = models.AsyncJobCall.objects.filter(started_at__lt=older_than)
    deleted_rows = queryset.delete()[0]
    if deleted_rows:
        logger.info(f'{deleted_rows} old Async job call models deleted')
