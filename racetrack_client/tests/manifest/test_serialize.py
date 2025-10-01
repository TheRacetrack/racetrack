import json

from racetrack_client.manifest.manifest import Manifest, GitManifest, ResourcesManifest
from racetrack_client.utils.quantity import Quantity
from racetrack_client.utils.datamodel import remove_none


def test_serialize_manifest_to_json():
    manifest = Manifest(
        name="golang-function",
        owner_email="nobody@example.com",
        jobtype="golang:latest",
        git=GitManifest(
            remote='https://github.com/TheRacetrack/racetrack',
            directory='sample/golang-function',
            branch='master',
        ),
        resources=ResourcesManifest(
            memory_min=Quantity('256Mi'),
            cpu_max=Quantity('1000m'),
        ),
    )
    model_dict = manifest.model_dump(mode="json")
    assert remove_none(model_dict) == {
        'name': "golang-function",
        'owner_email': "nobody@example.com",
        'jobtype': "golang:latest",
        'git': {
            'remote': 'https://github.com/TheRacetrack/racetrack',
            'directory': 'sample/golang-function',
            'branch': 'master',
        },
        'resources': {
            'memory_min': '256Mi',
            'cpu_max': '1000m',
        },
        'image_type': 'docker',  # default values applied
        'replicas': 1,
        'version': '0.0.1',
    }
    encoded_json: str = manifest.model_dump_json()
    assert json.loads(encoded_json) == manifest.model_dump()


def test_generate_json_schema_manifest():
    assert Manifest.model_json_schema()
