from racetrack_client.utils.request import parse_response, Requests
from image_builder.config import Config


def update_deployment_phase(config: Config, deployment_id: str, phase: str):
    r = Requests.put(
        f'{config.lifecycle_url}/api/v1/deploy{deployment_id}/phase',
        json={
            'phase': phase,
        },
    )
    parse_response(r, 'Lifecycle API error')
