import pytest
import httpretty

from racetrack_client.utils.request import Requests, parse_response, parse_response_object

_url = 'http://localhost/blahblah'


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_response_json():
    httpretty.register_uri(
        httpretty.GET,
        _url,
        status=200,
        body='{"result": "ok"}',
        content_type='application/json',
    )

    response = Requests.get(_url)
    parsed = parse_response_object(response, 'deploying error')

    assert parsed == {'result': 'ok'}


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_response_empty():
    httpretty.register_uri(
        httpretty.DELETE,
        _url,
        status=204,
        body='',
    )

    response = Requests.delete(_url)
    parsed = parse_response(response, 'deploying error')

    assert parsed is None


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_response_invalid_json():
    httpretty.register_uri(
        httpretty.GET,
        _url,
        status=200,
        body='',
        content_type='application/json',
    )

    response = Requests.get(_url)
    with pytest.raises(Exception) as excinfo:
        parse_response(response, 'deploying error')
    assert 'deploying error' in str(excinfo.value)
    assert 'no content in response to decode as JSON' in str(excinfo.value)


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_response_failed():
    httpretty.register_uri(
        httpretty.GET,
        _url,
        status=404,
        body='',
    )

    response = Requests.get(_url)
    with pytest.raises(Exception) as excinfo:
        parse_response(response, 'deploying error')
    assert (
        str(excinfo.value) == 'deploying error: 404 Not Found for url: http://localhost/blahblah'
    )


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_response_failed_gracefully_with_message():
    httpretty.register_uri(
        httpretty.GET,
        _url,
        status=500,
        body='{"error": "you have no power here"}',
        content_type='application/json',
    )

    response = Requests.get(_url)
    with pytest.raises(Exception) as excinfo:
        parse_response(response, 'deploying error')
    assert str(excinfo.value) == 'deploying error: Internal Server Error: you have no power here'
