from fastapi import APIRouter, Request
from fastapi.responses import Response, JSONResponse

from lifecycle.auth.authenticate import authenticate_token
from lifecycle.auth.authorize import authorize_internal_token, authorize_resource_access, grant_permission
from lifecycle.auth.subject import get_auth_subject_by_esc, get_auth_subject_by_job_family, regenerate_all_esc_tokens, regenerate_all_job_family_tokens, regenerate_all_user_tokens, regenerate_user_token
from lifecycle.config import Config
from lifecycle.auth.check import check_auth
from lifecycle.job.esc import read_esc_model
from lifecycle.job.models_registry import read_job_family_model
from racetrack_client.log.exception import log_exception
from racetrack_commons.auth.auth import AuthSubjectType, UnauthorizedError
from racetrack_client.log.logs import get_logger
from racetrack_commons.auth.scope import AuthScope

logger = get_logger(__name__)


def setup_auth_endpoints(api: APIRouter, config: Config):

    @api.get('/auth/allowed/job/{job_name}/{job_version}/scope/{scope}')
    def _auth_allowed_job(job_name: str, job_version: str, scope: str, request: Request):
        """Check if auth subject (read from token) has access to the job"""
        try:
            token_payload, auth_subject = authenticate_token(request)
            if token_payload.subject_type == AuthSubjectType.INTERNAL.value:
                authorize_internal_token(token_payload, scope, job_name, job_version)
            else:
                authorize_resource_access(auth_subject, job_name, job_version, scope)

        except UnauthorizedError as e:
            msg = e.describe(debug=config.auth_debug)
            log_exception(e)
            return JSONResponse(content={'error': msg}, status_code=401)

        return Response(content='', status_code=202)

    @api.get('/auth/allowed/job_endpoint/{job_name}/{job_version}/scope/{scope}/endpoint/{endpoint:path}')
    def _auth_allowed_job_endpoint(job_name: str, job_version: str, scope: str, endpoint: str, request: Request):
        """Check if auth subject (read from token) has access to the job endpoint"""
        if endpoint.endswith('/'):
            endpoint = endpoint[:-1]
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        try:
            token_payload, auth_subject = authenticate_token(request)
            if token_payload.subject_type == AuthSubjectType.INTERNAL.value:
                authorize_internal_token(token_payload, scope, job_name, job_version, endpoint)
            else:
                authorize_resource_access(auth_subject, job_name, job_version, scope, endpoint)

        except UnauthorizedError as e:
            msg = e.describe(debug=config.auth_debug)
            log_exception(e)
            return JSONResponse(content={'error': msg}, status_code=401)

        return Response(content='', status_code=202)

    @api.post('/auth/allow/esc/{esc_id}/job/{job_name}/scope/{scope}')
    def _auth_allow_esc_job_family(esc_id: str, job_name: str, scope: str, request: Request):
        """Grant ESC access to job family within a scope"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        esc_model = read_esc_model(esc_id)
        auth_subject = get_auth_subject_by_esc(esc_model)
        grant_permission(auth_subject, job_name, None, scope)

    @api.post('/auth/allow/job_family/{source_family_name}/job/{target_family_name}/scope/{scope}')
    def _auth_allow_family(source_family_name: str, target_family_name: str, scope: str, request: Request):
        """Grant Job family access to other job family within a scope"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        src_family_model = read_job_family_model(source_family_name)
        auth_subject = get_auth_subject_by_job_family(src_family_model)
        grant_permission(auth_subject, target_family_name, None, scope)

    @api.get('/auth/token/esc/{esc_id}')
    def _get_esc_token(esc_id: str, request: Request):
        """Get ESC auth token"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        esc_model = read_esc_model(esc_id)
        auth_subject = get_auth_subject_by_esc(esc_model)
        return {'token': auth_subject.token}

    @api.post('/auth/token/user/{username}/regenerate')
    def _generate_tokens_for_user(request: Request, username: str):
        """Generate new token for a User"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        regenerate_user_token(username)

    @api.post('/auth/token/user/regenerate')
    def _generate_tokens_for_all_users(request: Request):
        """Generate new tokens for all Users"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        regenerate_all_user_tokens()
        
    @api.post('/auth/token/job_family/regenerate')
    def _generate_tokens_for_all_job_families(request: Request):
        """Generate new tokens for all Job Families"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        regenerate_all_job_family_tokens()
        
    @api.post('/auth/token/esc/regenerate')
    def _generate_tokens_for_all_escs(request: Request):
        """Generate new tokens for all ESCs"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        regenerate_all_esc_tokens()
        
