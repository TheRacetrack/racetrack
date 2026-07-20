from typing import List, Dict, Optional
from urllib import request
import json

from racetrack_client.log.logs import get_logger

from settings import RESULTS_PER_PAGE, HEADERS

logger = get_logger(__name__)


def post_request(url: str, data):
    logger.debug(f'API request: POST {url}')
    jsondataasbytes = json.dumps(data).encode('utf-8')
    req = request.Request(url, method='POST')
    for name, value in HEADERS.items():
        req.add_header(name, value)
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    req.add_header('Content-Length', str(len(jsondataasbytes)))
    response = request.urlopen(req, jsondataasbytes)
    response_data = response.read().decode('utf8')
    if not response_data:
        return None
    return json.loads(response_data)


def delete_request(url: str):
    logger.debug(f'API request: DELETE {url}')
    req = request.Request(url, method='DELETE')
    for name, value in HEADERS.items():
        req.add_header(name, value)
    response = request.urlopen(req)
    response_data = response.read().decode('utf8')
    if not response_data:
        return None
    return json.loads(response_data)


def get_request(url: str, headers: Optional[Dict[str, str]] = None):
    if not headers:
        headers = {}
    logger.debug(f'API request: GET {url}')
    req = request.Request(url, method='GET')
    headers = headers or HEADERS
    for name, value in headers.items():
        req.add_header(name, value)
    response = request.urlopen(req)
    response_data = response.read().decode('utf8')
    if not response_data:
        return None
    return json.loads(response_data)


def get_request_paging(base_url: str) -> List:
    page = 1
    results = []

    while True:
        logger.debug(f'API request: GET {base_url}, page {page}')
        url = f'{base_url}&page={page}&per_page={RESULTS_PER_PAGE}' if '?' in base_url else f'{base_url}?page={page}&per_page={RESULTS_PER_PAGE}'

        req = request.Request(url, method='GET')
        for name, value in HEADERS.items():
            req.add_header(name, value)
        response = request.urlopen(req)
        response_data = response.read().decode('utf8')

        partial_response = json.loads(response_data)
        results.extend(partial_response)

        next_page = response.headers.get('x-next-page')
        if not next_page:
            break
        page += 1

    return results
