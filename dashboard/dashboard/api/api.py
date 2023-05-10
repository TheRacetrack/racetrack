import os

import httpx
from fastapi import FastAPI, Request, Response, Body
from starlette.background import BackgroundTask
from starlette.datastructures import MutableHeaders

from racetrack_client.log.logs import get_logger
from racetrack_client.utils.url import trim_url
from racetrack_commons.urls import get_external_lifecycle_url, get_external_pub_url
from dashboard.api.docs import setup_docs_endpoints

logger = get_logger(__name__)


def setup_api_endpoints(app: FastAPI):

    @app.get("/api/status")
    def _status():
        """Report current application status"""
        return {
            'service': 'dashboard',
            'live': True,
            'ready': True,
            'git_version': os.environ.get('GIT_VERSION', 'dev'),
            'docker_tag': os.environ.get('DOCKER_TAG', ''),
            'lifecycle_url': get_external_lifecycle_url(),
            'external_pub_url': get_external_pub_url(),
            'site_name': os.environ.get('SITE_NAME', ''),
        }
    
    setup_docs_endpoints(app)
    setup_proxy_endpoints(app)


def setup_proxy_endpoints(app: FastAPI):
    """Forward all API endpoints to Lifecycle service"""
    lifecycle_api_url = trim_url(os.environ.get('LIFECYCLE_URL', 'http://localhost:7202'))
    logger.info(f'Forwarding API requests to "{lifecycle_api_url}"')
    client = httpx.AsyncClient(base_url=f"{lifecycle_api_url}/")
    
    async def _proxy_api_call(request: Request, path: str, payload=Body(default={})):
        """Forward API call to Lifecycle service"""
        subpath = f'/api/v1/{request.path_params["path"]}'
        url = httpx.URL(path=subpath, query=request.url.query.encode("utf-8"))
        request_headers = MutableHeaders(request.headers)
        request_headers['referer'] = request.url.path

        timeout = httpx.Timeout(10, read=300)
        rp_req = client.build_request(request.method, url,
                                      headers=request_headers.raw,
                                      timeout=timeout,
                                      content=await request.body())
        httpx_response = await client.send(rp_req, stream=True)
        content: bytes = await httpx_response.aread()
        return Response(
            content=content,
            status_code=httpx_response.status_code,
            headers=httpx_response.headers,
            background=BackgroundTask(httpx_response.aclose),
        )

    app.router.add_api_route("/api/v1/{path:path}", _proxy_api_call,
                             methods=["GET", "POST", "PUT", "DELETE"])
