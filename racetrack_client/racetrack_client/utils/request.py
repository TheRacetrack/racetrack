import json
import ssl
from email.message import Message
from http.client import HTTPResponse
from http.client import responses
from typing import Any, List, Optional, Dict, Union
from urllib import request
from urllib.error import HTTPError, URLError
import urllib.parse as urlparse
from urllib.parse import urlencode

from racetrack_client.log.context_error import ContextError

DEBUG_MODE = False  # print the actual bytes sent in requests and responses


class RequestError(ContextError):
    """HTTP Request error due to network error, bad URL, unreachable address"""
    def __init__(self, error_context: str):
        super().__init__(error_context)


class ResponseError(RequestError):
    """HTTP error due to bad response code"""
    def __init__(self, error_context: str, status_code: int):
        super().__init__(error_context)
        self.status_code = status_code


class Response:

    def __init__(self,
        url: str,
        status_code: int,
        content: bytes,
        headers: Message,
    ):
        self._url: str = url
        self._status_code: int = status_code
        self._content: bytes = content
        self._headers: Message = headers

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def ok(self) -> bool:
        return self._status_code < 400

    def raise_for_status(self):
        if 400 <= self._status_code < 600:
            raise ResponseError(f'{self._status_code} {self.status_reason} for url: {self.url}', self._status_code)

    @property
    def status_reason(self) -> str:
        return responses[self._status_code]

    @property
    def content(self) -> bytes:
        return self._content

    @property
    def text(self) -> str:
        return self._content.decode('utf8')

    def json(self) -> Union[Dict, List]:
        response_data = self._content.decode('utf8')
        if not response_data:
            raise RuntimeError('no content in response to decode as JSON')
        return json.loads(response_data)

    @property
    def is_json(self) -> bool:
        return 'application/json' in self._headers['content-type']

    @property
    def url(self) -> str:
        return self._url
    
    @property
    def headers(self) -> Message:
        return self._headers
    
    def header(self, name: str) -> Optional[str]:
        return self._headers[name]


class Requests:

    insecure: bool = True  # whether to verify SSL certificates

    @classmethod
    def get(cls, 
            url: str,
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[float] = None,
        ) -> Response:
        return cls._make_request('GET', url, None, None, params, headers, timeout)

    @classmethod
    def post(cls,
            url: str,
            json: Optional[Any] = None,
            data: Optional[bytes] = None,
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[float] = None,
        ) -> Response:
        return cls._make_request('POST', url, json, data, params, headers, timeout)

    @classmethod
    def put(cls,
            url: str,
            json: Optional[Any] = None,
            data: Optional[bytes] = None,
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[float] = None,
        ) -> Response:
        return cls._make_request('PUT', url, json, data, params, headers, timeout)

    @classmethod
    def delete(cls,
            url: str,
            json: Optional[Any] = None,
            data: Optional[bytes] = None,
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[float] = None,
        ) -> Response:
        return cls._make_request('DELETE', url, json, data, params, headers, timeout)

    @classmethod
    def request(cls,
            method: str,
            url: str,
            json: Optional[Any] = None,
            data: Optional[bytes] = None,
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[float] = None,
        ) -> Response:
        return cls._make_request(method.upper(), url, json, data, params, headers, timeout)

    @classmethod
    def _make_request(cls, 
            method: str,
            url: str,
            jsondata: Optional[Any] = None,
            data: Optional[bytes] = None,
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[float] = None,
        ) -> Response:
        """
        Make HTTP request and return response object.
        :param method: HTTP method: GET, POST, PUT, DELETE
        :param url: URL starting with http(s)://
        :param jsondata: payload object to be serialized as JSON content
        :param data: raw payload bytes to be sent as HTTP content
        :param params: query params (at the end of path)
        :param headers: request headers
        :param timeout: timeout in seconds for blocking operations like the connection attempt
        (if not specified, the global default timeout setting will be used)
        :throws RequestError: if the request fails
        """
        if params:
            url = build_url_with_params(url, params)

        req = request.Request(url, method=method)
        kwargs: Dict[str, Any] = {}
        
        if headers:
            for name, value in headers.items():
                if value is not None:
                    req.add_header(name, value)

        if jsondata is not None:
            jsondataasbytes = json.dumps(jsondata).encode('utf-8')
            req.add_header('Content-Type', 'application/json; charset=utf-8')
            req.add_header('Content-Length', str(len(jsondataasbytes)))
            kwargs['data'] = jsondataasbytes
        elif data is not None:
            req.add_header('Content-Length', str(len(data)))
            kwargs['data'] = data
        
        if not req.has_header('Accept'):
            req.add_header('Accept', 'application/json, */*')

        if timeout is not None:
            kwargs['timeout'] = timeout

        if not req.has_header('User-Agent'):
            req.add_header('User-Agent', 'request')

        kwargs['context'] = cls._get_ssl_context()

        if DEBUG_MODE:
            http_handler = request.HTTPHandler(debuglevel=2)
            https_handler = request.HTTPSHandler(context=kwargs['context'], debuglevel=2)
            opener = request.build_opener(http_handler, https_handler)
            request.install_opener(opener)
            # Passing 'context' argument to urllib.request.urlopen rebuilds the URL opener,
            # not giving a chance to turn the debug mode on.
            del kwargs['context']

        try:
            http_response: HTTPResponse = request.urlopen(req, **kwargs)
            return Response(
                url=url,
                status_code=http_response.status,
                content=http_response.read(),
                headers=http_response.headers,
            )
        except HTTPError as e:
            return Response(
                url=url,
                status_code=e.code,
                content=e.read(),
                headers=e.headers,
            )
        except URLError as e:
            raise RequestError(f'Request failed: {method} {url}') from e
        except BaseException as e:
            raise RequestError('Request failed') from e

    @classmethod
    def _get_ssl_context(cls) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        if cls.insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx


def build_url_with_params(
    base_url: str,
    params: Dict[str, Any],
) -> str:
    url_parts = list(urlparse.urlparse(base_url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlparse.urlunparse(url_parts)
    

def parse_response(response: Response, error_context: str) -> Optional[Union[Dict, List]]:
    """
    Ensure response was successful. If not, try to extract error message from it.
    :return: response parsed as JSON object

    This function handles all of these following cases:
    - if request went fine, return parsed JSON object,
    - if request went fine, but response is empty (eg. 204 status after DELETing), return None
    - if request went fine, but there was eg. JSON parsing error,
     raise "Deployment error: Json is invalid in character 5"
    - if request completely failed with empty response (eg. due to Kubernetes issues),
    raise "Deployment error: 404 Not found for url http://localhost/blahblah"
    - if request failed gracefully from other RT component returning {"error": "you have no power here"},
    raise "Deployment error: 500 Internal Server Error: you have no power here"
    """
    try:
        result: Optional[Union[Dict, List]] = None
        if 'application/json' in response.headers['content-type']:
            result = response.json()

        if response.ok:
            return result

        if result is not None and isinstance(result, dict) and 'error' in result:
            raise RuntimeError(f'{response.status_reason}: {result.get("error")}')
        raise ResponseError(f'{response.status_code} {response.status_reason} for url: {response.url}', response._status_code)
    except Exception as e:
        raise ResponseError(error_context, response.status_code) from e


def parse_response_object(response: Response, error_context: str) -> Dict:
    try:
        if 'application/json' not in response.headers['content-type']:
            raise RuntimeError(f'expected JSON response, got "{response.headers["content-type"]}" for url: {response.url}')

        result = response.json()

        if response.ok:
            assert isinstance(result, dict), f'response JSON expected to be a dictionary, got {type(result)}'
            return result

        if result is not None and isinstance(result, dict) and 'error' in result:
            raise RuntimeError(f'{response.status_reason}: {result.get("error")}')
        raise ResponseError(f'{response.status_code} {response.status_reason} for url: {response.url}', response._status_code)
    except Exception as e:
        raise ResponseError(error_context, response.status_code) from e


def parse_response_list(response: Response, error_context: str) -> List:
    try:
        if 'application/json' not in response.headers['content-type']:
            raise RuntimeError(f'expected JSON response, got "{response.headers["content-type"]}" for url: {response.url}')

        result = response.json()

        if response.ok:
            assert isinstance(result, list), f'response JSON expected to be a list, got {type(result)}'
            return result

        if result is not None and isinstance(result, dict) and 'error' in result:
            raise RuntimeError(f'{response.status_reason}: {result.get("error")}')
        raise ResponseError(f'{response.status_code} {response.status_reason} for url: {response.url}', response._status_code)
    except Exception as e:
        raise ResponseError(error_context, response.status_code) from e
