

from racetrack_client.utils.datamodel import parse_dict_datamodels
from racetrack_commons.entities.dto import FatmanDto


def test_convert_json_to_fatman_dto():
    response = [
        {
            'name': 'skynet',
            'version': '1.0.0',
            'status': 'RUNNING',
            'create_time': 5,
            'update_time': 7,
            'id': '1',
            'manifest': {
                'name': 'skynet',
                'owner_email': 'arnold@skynet.com',
                'git': {
                    'remote': 'https://github.com',
                },
                'lang': 'python3',
                'resources': {
                    'memory_min': '1Gi',
                    'cpu_min': 1,
                    'cpu_max': None,
                },
            },
            'internal_name': 'skynet-v-1-0-0',
            'pub_url': None,
            'error': None,
            'image_tag': None,
        },
    ]
    fatmen = parse_dict_datamodels(response, FatmanDto)
    fatman = fatmen[0]

    assert fatman.name == 'skynet'
    assert fatman.manifest.name == 'skynet'
    assert fatman.error is None
    assert str(fatman.manifest.resources.memory_min) == '1Gi'
    assert fatman.manifest.resources.memory_min.plain_number == 1024**3
    assert fatman.manifest.resources.memory_max is None
    assert fatman.manifest.resources.cpu_min.plain_number == 1
    assert fatman.manifest.resources.cpu_max is None
