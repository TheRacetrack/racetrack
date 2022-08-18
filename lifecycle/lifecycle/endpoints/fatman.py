from typing import Any, Dict, Optional
from fastapi import APIRouter, Request
from opentelemetry import trace

from lifecycle.auth.check import check_auth
from lifecycle.config import Config
from lifecycle.deployer.redeploy import redeploy_fatman, reprovision_fatman
from lifecycle.fatman.graph import build_fatman_dependencies_graph
from lifecycle.fatman.registry import (
    delete_fatman,
    list_fatman_families,
    list_fatmen_registry,
    read_versioned_fatman,
)
from lifecycle.fatman.public_endpoints import read_active_fatman_public_endpoints
from lifecycle.fatman.logs import read_build_logs, read_runtime_logs
from pydantic import BaseModel, Field
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.auth.authenticate import get_username_from_token
from racetrack_commons.auth.scope import AuthScope


def setup_fatman_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):

    class FatmanResultModel(BaseModel):
        id: Optional[str] = Field(
            default=None,
            description='ID of fatman',
            example='00000000-1111-2222-3333-444444444444',
        )
        name: Optional[str] = Field(
            default=None,
            description='name of Fatman',
            example='adder',
        )
        version: Optional[str] = Field(
            default=None,
            description='version of Fatman',
            example='0.0.1',
        )
        deployed_by: Optional[str] = Field(
            default=None,
            description='username of the last deployer',
            example='nobody',
        )
        manifest: Dict[str, Any] = Field(
            description='Manifest - build recipe for a Fatman',
            example={
                'name': 'adder',
                'lang': 'python3',
                'owner_email': 'nobody@example.com',
                'git': {
                    'remote': '.',
                    'directory': 'sample/python-class',
                },
                'python': {
                    'requirements_path': 'requirements.txt',
                    'entrypoint_path': 'adder.py',
                },
            },
        )
        error: Optional[str] = Field(
            default=None,
            description='error message',
            example='you have no power here',
        )
        status: Optional[str] = Field(
            default=None,
            description='status name',
            example='all ok',
        )
        internal_name: Optional[str] = Field(
            default=None,
            description='internal name of the fatman',
            example='fatman-adder-v-0-0-1',
        )
        create_time: Optional[int] = Field(
            default=None,
            description='timestamp of creation',
            example=1000000,
        )
        update_time: Optional[int] = Field(
            default=None,
            description='timestamp of last update',
            example=1000000,
        )

    tracer = trace.get_tracer(__name__)

    @api.get('/fatman')
    def _list_all_fatmen(request: Request):
        """Get list of deployed Fatman"""
        with tracer.start_as_current_span("get-fatman-list") as span:
            span.set_attribute("endpoint.method", 'GET')
            span.set_attribute("endpoint.path", '/fatman')

            auth_subject = check_auth(request, scope=AuthScope.READ_FATMAN)
            return list_fatmen_registry(config, auth_subject)

    @api.get('/fatman_family')
    def _get_fatman_family(request: Request):
        """Get list of deployed Fatman Families (names regardless version)"""
        auth_subject = check_auth(request, scope=AuthScope.READ_FATMAN)
        return list_fatman_families(auth_subject)

    @api.get('/fatman_graph')
    def _get_fatman_graph(request: Request):
        """Get Fatman dependencies graph"""
        auth_subject = check_auth(request, scope=AuthScope.READ_FATMAN)
        return build_fatman_dependencies_graph(config, auth_subject)

    @api.get('/fatman/{fatman_name}/{fatman_version}', response_model=FatmanResultModel)
    def _get_fatman(fatman_name: str, fatman_version: str, request: Request):
        """Get details of particular Fatman"""
        check_auth(request, fatman_name=fatman_name, fatman_version=fatman_version, scope=AuthScope.READ_FATMAN)
        return read_versioned_fatman(fatman_name, fatman_version, config)

    @api.delete('/fatman/{fatman_name}/{fatman_version}')
    def _delete_fatman(fatman_name: str, fatman_version: str, request: Request):
        """Delete Fatman; expects specific version (can't be latest)"""
        check_auth(request, fatman_name=fatman_name, fatman_version=fatman_version, scope=AuthScope.DELETE_FATMAN)
        username = get_username_from_token(request)
        return delete_fatman(fatman_name, fatman_version, config, username, plugin_engine)

    @api.post('/fatman/{fatman_name}/{fatman_version}/redeploy')
    def _redeploy_fatman(fatman_name, fatman_version: str, request: Request):
        """Deploy specific Fatman image once again (build and provision)"""
        auth_subject = check_auth(request, fatman_name=fatman_name, fatman_version=fatman_version, scope=AuthScope.DEPLOY_FATMAN)
        username = get_username_from_token(request)
        return redeploy_fatman(fatman_name, fatman_version, config, plugin_engine, username, auth_subject)

    @api.post('/fatman/{fatman_name}/{fatman_version}/reprovision')
    def _reprovision_fatman(fatman_name, fatman_version: str, request: Request):
        """Provision specific Fatman image once again to a cluster"""
        auth_subject = check_auth(request, fatman_name=fatman_name, fatman_version=fatman_version, scope=AuthScope.DEPLOY_FATMAN)
        username = get_username_from_token(request)
        return reprovision_fatman(fatman_name, fatman_version, config, plugin_engine, username, auth_subject)

    @api.get('/fatman/{fatman_name}/{fatman_version}/logs')
    def _get_fatman_logs(request: Request, fatman_name: str, fatman_version: str, tail: int = 20):
        """Get last logs of particular Fatman"""
        check_auth(request, fatman_name=fatman_name, fatman_version=fatman_version, scope=AuthScope.READ_FATMAN)
        return {'logs': read_runtime_logs(fatman_name, fatman_version, tail, config, plugin_engine)}

    @api.get('/fatman/{fatman_name}/{fatman_version}/build-logs')
    def _get_fatman_build_logs(request: Request, fatman_name: str, fatman_version: str, tail: int = 0):
        """Get build logs of Fatman deployment attempt"""
        check_auth(request, fatman_name=fatman_name, fatman_version=fatman_version, scope=AuthScope.READ_FATMAN)
        return {'logs': read_build_logs(fatman_name, fatman_version, tail)}

    @api.get("/fatman/{fatman_name}/{fatman_version}/public-endpoints")
    def _get_fatman_public_endpoints(request: Request, fatman_name: str, fatman_version: str):
        """Get list of active public endpoints that can be accessed without authentication for a particular Fatman"""
        check_auth(request, fatman_name=fatman_name, fatman_version=fatman_version, scope=AuthScope.READ_FATMAN)
        return read_active_fatman_public_endpoints(fatman_name, fatman_version)
