import os

from racetrack_client.utils.request import parse_response, Requests
from racetrack_client.utils.auth import RT_AUTH_HEADER
from racetrack_client.log.logs import get_logger
from image_builder.config import Config

logger = get_logger(__name__)


def update_deployment_phase(config: Config, deployment_id: str, phase: str):
    if not config.lifecycle_url:
        return

    logger.info(f'updating deployment {deployment_id} phase: {phase}')
    r = Requests.put(
        f'{config.lifecycle_url}/api/v1/deploy/{deployment_id}/phase',
        json={
            'phase': phase,
        },
        headers={
            RT_AUTH_HEADER: os.environ.get('LIFECYCLE_AUTH_TOKEN'),
        },
    )
    parse_response(r, 'Lifecycle API error')
