from fastapi.testclient import TestClient

from fatman_wrapper.api import create_api_app
from fatman_wrapper.entrypoint import FatmanEntrypoint
from fatman_wrapper.health import HealthState


def test_static_endpoints():
    class TestEntrypoint(FatmanEntrypoint):
        def perform(self):
            pass

        def static_endpoints(self):
            return {
                '/xrai': ('sample/static_endpoints/xrai.yaml', 'application/x-yaml'),
                '/docs': './sample/static_endpoints/docs',
            }

    entrypoint = TestEntrypoint()
    api_app = create_api_app(entrypoint, HealthState(live=True, ready=True))

    client = TestClient(api_app)

    response = client.get('/api/v1/xrai')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/x-yaml'
    assert response.content == b'name: Skynet'

    response = client.get('/api/v1/docs')
    assert response.status_code == 404

    response = client.get('/api/v1/docs/subfolder/index.html')
    assert response.status_code == 200
    assert 'text/html' in response.headers['Content-Type']
    assert response.content == b'<body>index</body>'

    response = client.get('/api/v1/docs/subfolder/Readme.md')
    assert response.status_code == 200
    assert 'text/markdown' in response.headers['Content-Type']
    assert response.content == b'# Readme'
