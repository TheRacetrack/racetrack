from fastapi.testclient import TestClient

from image_builder.config import Config
from image_builder.api import configure_api
from racetrack_commons.plugin.engine import PluginEngine


def test_metrics_endpoint():
    api_app = configure_api(Config(), PluginEngine())

    client = TestClient(api_app)

    response = client.get('/metrics')
    assert response.status_code == 200
    data = response.text
    assert 'images_buidling_errors' in data
