import os

from racetrack_client.utils.request import parse_response, Requests
from racetrack_client.utils.auth import RT_AUTH_HEADER
from image_builder.config import Config


def update_deployment_phase(config: Config, deployment_id: str, phase: str):
    if not config.lifecycle_url:
        return

    r = Requests.put(
        f'{config.lifecycle_url}/api/v1/deploy/{deployment_id}/phase',
        json={
            'phase': phase,
        },
        headers={
            RT_AUTH_HEADER: os.environ.get('LIFECYCLE_TOKEN'),
        },
    )
    parse_response(r, 'Lifecycle API error')
