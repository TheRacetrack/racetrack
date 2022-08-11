import pytest
import httpretty

from lifecycle.monitor.health import check_until_fatman_is_operational

_base_url = 'http://localhost'


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_liveness_readiness_fine():
    httpretty.register_uri(
        httpretty.GET,
        _base_url + '/live',
        status=200,
        body='{"live": true, "deployment_timestamp": 1000}',
        content_type='application/json',
    )
    httpretty.register_uri(
        httpretty.GET,
        _base_url + '/ready',
        status=200,
        body='{"ready": true}',
        content_type='application/json',
    )

    check_until_fatman_is_operational(_base_url, deployment_timestamp=1000)


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_liveness_error():
    httpretty.register_uri(
        httpretty.GET,
        _base_url + '/live',
        status=500,
        body='{"live": false, "deployment_timestamp": 1000, "error": "you have no power here"}',
        content_type='application/json',
    )
    httpretty.register_uri(
        httpretty.GET,
        _base_url + '/ready',
        status=500,
        body='{"ready": false}',
        content_type='application/json',
    )

    with pytest.raises(Exception) as excinfo:
        check_until_fatman_is_operational(_base_url, deployment_timestamp=1000)
    assert 'you have no power here' in str(excinfo.value)
    assert 'Fatman initialization error' in str(excinfo.value)
