from datetime import timedelta

from lifecycle.database.condition_builder import QueryCondition
from racetrack_client.utils.time import now
from racetrack_client.log.logs import get_logger
from lifecycle.config import Config
from lifecycle.database.schema import tables
from lifecycle.server.cache import LifecycleCache

logger = get_logger(__name__)


def clean_up_async_job_calls(config: Config):
    older_than = now() - timedelta(seconds=config.async_job_call_lifetime)

    mapper = LifecycleCache.record_mapper()
    condition = QueryCondition(f'started_at < {mapper.placeholder}', older_than)
    records = mapper.filter(tables.AsyncJobCall, condition=condition)
    
    if records:
        for record in records:
            mapper.delete_record(record)
        logger.info(f'{len(records)} old Async job call models deleted')
