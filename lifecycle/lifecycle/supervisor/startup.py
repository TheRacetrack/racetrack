from racetrack_client.log.logs import get_logger
from racetrack_client.utils.time import datetime_to_timestamp, days_ago, now
from racetrack_commons.entities.dto import DeploymentStatus
from lifecycle.job.deployment import list_deployments_by_status

logger = get_logger(__name__)


def startup_check():
    in_progress_deployments = list_deployments_by_status(DeploymentStatus.IN_PROGRESS.value)

    in_progress_deployments = [deployment for deployment in in_progress_deployments if
                               days_ago(datetime_to_timestamp(deployment.update_time)) * 24 >= 1]

    if in_progress_deployments:
        logger.info(f'Halting {len(in_progress_deployments)} stale IN_PROGRESS deployments')
        for deployment in in_progress_deployments:

            deployment.status = DeploymentStatus.FAILED.value
            deployment.error = 'halted due to server restart'
            deployment.update_time = now()
            deployment.save()
