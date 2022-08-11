from typing import Dict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

from racetrack_commons.api.asgi.access_log import enable_request_access_log, enable_response_access_log
from racetrack_commons.api.asgi.error_handler import register_error_handlers
from racetrack_commons.api.asgi.proxy import TrailingSlashForwarder
from racetrack_commons.api.response import register_response_json_encoder


def create_fastapi(
    title: str,
    description: str,
    base_url: str = '',
    version: str = '',
    authorizations: Dict = None,
    request_access_log: bool = False,
    response_access_log: bool = True,
) -> FastAPI:

    fastapi_app = create_fastapi_docs(
        title, description, base_url, version, authorizations,
    )

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(fastapi_app)
    register_response_json_encoder()

    if request_access_log:
        enable_request_access_log(fastapi_app)
    if response_access_log:
        enable_response_access_log(fastapi_app)

    fastapi_app.add_middleware(TrailingSlashForwarder)

    return fastapi_app
   

def create_fastapi_docs(
    title: str,
    description: str,
    base_url: str = '',
    version: str = '',
    authorizations: Dict = None,
) -> FastAPI:
    version = version or '1.0.0'

    servers = [{"url": "/", "description": "root base path"}]
    if base_url:
        servers.insert(0, {"url": base_url, "description": "proxy prefixed path"})

    fastapi_app = FastAPI(
        title=title,
        description=description,
        version=version,
        docs_url='/',
        servers=servers,
        swagger_ui_parameters={
            'displayRequestDuration': True,
        },
    )

    authorizations = authorizations or {}

    def custom_openapi():
        if fastapi_app.openapi_schema:
            return fastapi_app.openapi_schema
        openapi_schema = get_openapi(
            title=title,
            description=description,
            version=version,
            servers=servers,
            routes=fastapi_app.routes,
        )

        if authorizations:
            if 'components' not in openapi_schema:
                openapi_schema['components'] = {}
            if 'securitySchemes' not in openapi_schema['components']:
                openapi_schema['components']['securitySchemes'] = {}
            openapi_schema['components']['securitySchemes'] = authorizations

            if 'security' not in openapi_schema:
                openapi_schema['security'] = []
            for key in authorizations.keys():
                openapi_schema['security'].append({
                    key: [],
                })

        fastapi_app.openapi_schema = openapi_schema
        return fastapi_app.openapi_schema

    fastapi_app.openapi = custom_openapi

    return fastapi_app
