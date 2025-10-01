from dataclasses import dataclass
from typing import Dict, Optional

from racetrack_client.utils.datamodel import convert_to_json
from racetrack_client.client_config.client_config import Credentials


@dataclass
class SampleDataclass:
    credentials: Optional[Credentials]
    secrets: Dict[str, str]


def test_convert_to_json():
    assert convert_to_json(None) == 'null'
    assert convert_to_json(SampleDataclass(credentials=None, secrets={})) \
        == '{"secrets": {}}', 'it should trim null values'
    assert convert_to_json(SampleDataclass(
        credentials=Credentials(username='alice', password='secret'),
        secrets={'key1': 'nonempty', 'other': None})) \
        == '{"credentials": {"username": "alice", "password": "secret"}, "secrets": {"key1": "nonempty"}}'
