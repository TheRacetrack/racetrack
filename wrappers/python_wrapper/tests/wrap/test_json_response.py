from dataclasses import dataclass

from fastapi.testclient import TestClient

from fatman_wrapper.api import create_api_app
from fatman_wrapper.health import HealthState
from fatman_wrapper.wrapper import create_entrypoint_app
from racetrack_client.manifest.manifest import GitManifest, Manifest, ResourcesManifest
from racetrack_client.utils.datamodel import remove_none
from racetrack_client.utils.quantity import Quantity


def test_serialize_numpy_array():
    api_app = create_entrypoint_app('sample/numpy_response_model.py')

    client = TestClient(api_app)

    response = client.post('/api/v1/perform', json={})
    assert response.status_code == 200
    output = response.json()
    assert output == [1, 2, 3]


@dataclass
class DataClassy:
    name: str
    age: int
    is_classy: bool


def test_serialize_dataclass():
    class TestEntrypoint:
        def perform(self):
            return DataClassy(name='Data', age=30, is_classy=True)

    entrypoint = TestEntrypoint()
    api_app = create_api_app(entrypoint, HealthState(live=True, ready=True))

    client = TestClient(api_app)

    response = client.post('/api/v1/perform', json={})
    assert response.status_code == 200
    assert response.json() == {'name': 'Data', 'age': 30, 'is_classy': True}


def test_serialize_quantity():
    class TestEntrypoint:
        def perform(self):
            return [
                Quantity('100Mi'),
                {
                    'quantity': Quantity('1000m'),
                },
                Manifest(
                    name='test',
                    owner_email='nobody',
                    git=GitManifest(
                        remote='url',
                        directory='.',
                    ),
                    resources=ResourcesManifest(
                        memory_min=Quantity('1Gi'),
                    ),
                    image_type='docker',
                    lang='python3',
                    replicas=1,
                    version='0.0.1',
                ),
            ]

    entrypoint = TestEntrypoint()

    api_app = create_api_app(entrypoint, HealthState(live=True, ready=True))

    client = TestClient(api_app)

    response = client.post('/api/v1/perform', json={})
    assert response.status_code == 200
    assert response.json()[:2] == [
        '100Mi',
        {'quantity': '1000m'},
    ]
    assert remove_none(response.json()[2]) == {
        'name': 'test',
        'owner_email': 'nobody',
        'git': {
            'remote': 'url',
            'directory': '.',
        },
        'resources': {
            'memory_min': '1Gi',
        },
        'image_type': 'docker',
        'lang': 'python3',
        'replicas': 1,
        'version': '0.0.1',
    }
