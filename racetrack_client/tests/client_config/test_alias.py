from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.client_config import ClientConfig


def test_resolve_lifecycle_url():
    client_config = ClientConfig(lifecycle_url_aliases={
        'dev': 'https://dev-cluster/lifecycle',
        'kind': 'http://127.0.0.1:7002',
    })

    # resolve from alias
    assert resolve_lifecycle_url(client_config, 'dev') == 'https://dev-cluster/lifecycle'
    assert resolve_lifecycle_url(client_config, 'kind') == 'http://127.0.0.1:7002/lifecycle'
    # default from ClientConfig
    assert resolve_lifecycle_url(client_config, '') == 'http://127.0.0.1:7002/lifecycle'
    # unchanged direct URL
    assert resolve_lifecycle_url(client_config, 'https://test-cluster/lifecycle') ==\
           'https://test-cluster/lifecycle'

    # Infer full lifecycle URL
    assert resolve_lifecycle_url(client_config, 'http://test-cluster') == 'http://test-cluster/lifecycle'
    assert resolve_lifecycle_url(client_config, 'test-cluster') == 'https://test-cluster/lifecycle'
    assert resolve_lifecycle_url(client_config, 'test-cluster/lifecycle') ==\
           'https://test-cluster/lifecycle'
    assert resolve_lifecycle_url(client_config, 'http://test-cluster/') == 'http://test-cluster/'
    assert resolve_lifecycle_url(client_config, 'test-cluster:7002') == 'https://test-cluster:7002/lifecycle'
