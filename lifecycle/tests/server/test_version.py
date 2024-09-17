import os

import pytest
from fastapi.testclient import TestClient

from lifecycle.config import Config
from lifecycle.server.metrics_collector import unregister_metrics
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.server.api import create_fastapi_app


@pytest.mark.django_db(transaction=True)
def test_health_version_endpoint():
    os.environ['GIT_VERSION'] = '0.0.1-g32c4b29-dirty'
    os.environ['DJANGO_DB_TYPE'] = 'sqlite'
    unregister_metrics()
    fastapi_app = create_fastapi_app(Config(), PluginEngine(), 'lifecycle')

    client = TestClient(fastapi_app)

    response = client.get('/health')
    assert response.status_code == 200, f'Wrong response: {response.content}'
    obj = response.json()
    assert obj['git_version'] == '0.0.1-g32c4b29-dirty'
    assert obj['live'] is True

