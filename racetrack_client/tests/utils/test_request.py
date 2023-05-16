import pytest
import httpretty

from racetrack_client.utils.request import Requests, build_url_with_params

_url = 'http://localhost/blahblah'


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_request_get_json():
    httpretty.register_uri(
        httpretty.GET,
        _url,
        status=200,
        body='{"result": "ok"}',
        content_type='application/json',
    )

    response = Requests.get(_url)
    assert response.status_code == 200
    assert response.ok
    response.raise_for_status()
    assert response.status_reason == 'OK'
    assert response.content == b'{"result": "ok"}'
    assert response.text == '{"result": "ok"}'
    assert response.json() == {'result': 'ok'}
    assert response.url == _url
    assert response.headers['content-type'] == 'application/json'
    assert response.headers['Content-Type'] == 'application/json'
    assert response.header('content-type') == 'application/json'
    assert response.header('Content-Type') == 'application/json'
    assert response.header('X-Nothing') is None


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_request_delete_with_empty_response():
    httpretty.register_uri(
        httpretty.DELETE,
        _url,
        status=204,
        body='',
    )

    response = Requests.delete(_url)
    assert response.status_code == 204
    assert response.ok
    response.raise_for_status()
    assert response.status_reason == 'No Content'
    assert response.content == b''
    assert response.text == ''
    with pytest.raises(Exception):
        response.json()


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_request_post_json_data():
    httpretty.register_uri(
        httpretty.POST,
        _url,
        status=201,
        body='',
    )

    response = Requests.post(_url, {'object': {'subobject': 17}})
    assert response.status_code == 201
    assert response.ok
    response.raise_for_status()
    assert response.status_reason == 'Created'
    assert response.content == b''
    assert response.text == ''


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
    assert response.status_code == 200
    assert response.ok
    response.raise_for_status()
    assert response.status_reason == 'OK'
    assert response.content == b''
    assert response.text == ''
    with pytest.raises(Exception):
        response.json()


@httpretty.activate(verbose=True, allow_net_connect=False)
def test_response_error():
    httpretty.register_uri(
        httpretty.GET,
        _url,
        status=404,
        body='{"error": "nothing"}',
        content_type='application/json',
    )

    response = Requests.get(_url)
    assert response.status_code == 404
    assert not response.ok
    with pytest.raises(Exception):
        response.raise_for_status()
    assert response.status_reason == 'Not Found'
    assert response.json() == {'error': 'nothing'}
    assert response.headers['content-type'] == 'application/json'
    assert response.headers['Content-Type'] == 'application/json'
    assert response.header('content-type') == 'application/json'
    assert response.header('Content-Type') == 'application/json'
    assert response.header('X-Nothing') is None


def test_build_url_with_params():
    url = "http://example.com/search"
    params = {'lang': 'en', 'tag': 'this is a sentence?! &'}
    assert build_url_with_params(url, params) == "http://example.com/search?lang=en&tag=this+is+a+sentence%3F%21+%26"

    url = "http://example.com/search?q=question"
    params = {'lang': 'en', 'tag': 'this is a sentence?! &'}
    assert build_url_with_params(url, params) == "http://example.com/search?q=question&lang=en&tag=this+is+a+sentence%3F%21+%26"
