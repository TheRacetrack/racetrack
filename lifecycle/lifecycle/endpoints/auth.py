from fastapi import APIRouter, Request
from fastapi.responses import Response, JSONResponse

from lifecycle.auth.authenticate import authenticate_token
from lifecycle.auth.authorize import authorize_internal_token, authorize_resource_access, grant_permission
from lifecycle.auth.subject import get_auth_subject_by_esc, get_auth_subject_by_fatman_family
from lifecycle.config import Config
from lifecycle.auth.check import check_auth
from lifecycle.fatman.esc import read_esc_model
from lifecycle.fatman.models_registry import read_fatman_family_model
from racetrack_client.log.exception import log_exception
from racetrack_commons.auth.auth import AuthSubjectType, UnauthorizedError
from racetrack_client.log.logs import get_logger
from racetrack_commons.auth.scope import AuthScope

logger = get_logger(__name__)


def setup_auth_endpoints(api: APIRouter, config: Config):

    @api.get('/auth/allowed/fatman/{fatman_name}/{fatman_version}/scope/{scope}')
    def _auth_allowed_fatman(fatman_name: str, fatman_version: str, scope: str, request: Request):
        """Check if auth subject (read from token) has access to the fatman family"""
        try:
            token_payload, auth_subject = authenticate_token(request)
            if token_payload.subject_type == AuthSubjectType.INTERNAL.value:
                authorize_internal_token(token_payload, scope, fatman_name, fatman_version)
            else:
                authorize_resource_access(auth_subject, fatman_name, fatman_version, scope)

        except UnauthorizedError as e:
            msg = e.describe(debug=config.auth_debug)
            log_exception(e)
            return JSONResponse(content={'error': msg}, status_code=401)

        return Response(content='', status_code=202)

    @api.post('/auth/allow/esc/{esc_id}/fatman/{fatman_name}/scope/{scope}')
    def _auth_allow_esc_fatman_family(esc_id: str, fatman_name: str, scope: str, request: Request):
        """Grant ESC access to fatman family within a scope"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        esc_model = read_esc_model(esc_id)
        auth_subject = get_auth_subject_by_esc(esc_model)
        grant_permission(auth_subject, fatman_name, None, scope)

    @api.post('/auth/allow/fatman_family/{source_family_name}/fatman/{target_family_name}/scope/{scope}')
    def _auth_allow_family(source_family_name: str, target_family_name: str, scope: str, request: Request):
        """Grant Fatman family access to other fatman family within a scope"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        src_family_model = read_fatman_family_model(source_family_name)
        auth_subject = get_auth_subject_by_fatman_family(src_family_model)
        grant_permission(auth_subject, target_family_name, None, scope)

    @api.get('/auth/token/esc/{esc_id}')
    def _get_esc_token(esc_id: str, request: Request):
        """Get ESC auth token"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        esc_model = read_esc_model(esc_id)
        auth_subject = get_auth_subject_by_esc(esc_model)
        return {'token': auth_subject.token}
