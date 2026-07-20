from fastapi.testclient import TestClient

from image_builder.config import Config
from image_builder.api import configure_api
from racetrack_client.utils.shell import shell, CommandError
from racetrack_commons.plugin.engine import PluginEngine


def test_health_endpoint():
    api_app = configure_api(Config(), PluginEngine())

    client = TestClient(api_app)

    response = client.get('/health')
    if _is_docker_available():
        assert response.status_code == 200, f'unexpected response: {response}'
        obj = response.json()
        assert obj['status'] == 'pass'
    else:
        assert response.status_code == 500, f'unexpected response: {response}'
        obj = response.json()
        assert obj['status'] == 'fail'


def _is_docker_available() -> bool:
    try:
        shell('docker ps')
        return True
    except CommandError:
        return False
