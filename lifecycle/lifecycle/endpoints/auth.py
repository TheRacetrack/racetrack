from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response, JSONResponse

from lifecycle.auth.authenticate import authenticate_token
from lifecycle.auth.authorize import authorize_internal_token, authorize_resource_access, grant_permission
from lifecycle.auth.cookie import set_auth_token_cookie
from lifecycle.auth.subject import get_auth_subject_by_esc, get_auth_subject_by_job_family, regenerate_all_esc_tokens, regenerate_all_job_family_tokens, regenerate_all_user_tokens, regenerate_specific_user_token
from lifecycle.config import Config
from lifecycle.auth.check import check_auth
from lifecycle.django.registry import models
from lifecycle.job import models_registry
from lifecycle.job.dto_converter import job_model_to_dto
from lifecycle.job.esc import read_esc_model
from lifecycle.job.models_registry import read_job_family_model
from lifecycle.job.public_endpoints import read_job_model_public_endpoints
from racetrack_client.log.exception import log_exception
from racetrack_commons.auth.auth import AuthSubjectType, UnauthorizedError
from racetrack_client.log.logs import get_logger
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.entities.dto import JobDto

logger = get_logger(__name__)

unprotected_job_endpoints = {
    "/health",
    "/live",
    "/ready",
}


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
        endpoint = _normalize_endpoint_path(endpoint)
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
    
    @api.get('/auth/can-call-job/{job_name}/{job_version}/{endpoint:path}', response_model=JobDto)
    def _auth_can_call_job_endpoint(job_name: str, job_version: str, endpoint: str, request: Request):
        """
        Check if auth subject (read from token) is allowed to call an endpoint of a job.
        This is intended to check all permissions with a single request made by PUB.
        """
        endpoint = _normalize_endpoint_path(endpoint)

        job_model = models_registry.resolve_job_model(job_name, job_version)
        
        try:
            _authorize_job_caller(job_model, endpoint, request)
            return job_model_to_dto(job_model, config)

        except UnauthorizedError as e:
            msg = e.describe(debug=config.auth_debug)
            log_exception(e)
            return JSONResponse(content={'error': msg}, status_code=401)

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

    @api.post('/auth/token/user/regenerate')
    def _generate_tokens_for_user(request: Request) -> JSONResponse:
        """Generate new token for a User"""
        auth_subject = check_auth(request, subject_types=[AuthSubjectType.USER])
        new_token = regenerate_specific_user_token(auth_subject)
        response = JSONResponse({
            'new_token': new_token,
        })
        set_auth_token_cookie(new_token, response)
        return response

    @api.post('/auth/token/user/all/regenerate')
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
        

def _normalize_endpoint_path(endpoint: str) -> str:
    if endpoint.endswith('/'):
        endpoint = endpoint[:-1]
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
    return endpoint


def _authorize_job_caller(job_model: models.Job, endpoint: str, request: Request):
    """
    Check if auth subject (read from request header's token) is allowed to call an endpoint of a job.
    In case it's not allowed, raise UnauthorizedError.
    """
    if endpoint in unprotected_job_endpoints:
        return

    # check public endpoints
    public_endpoints: list[str] = read_job_model_public_endpoints(job_model)
    for public_endpoint in public_endpoints:
        if endpoint.startswith(public_endpoint):
            return
    
    scope = AuthScope.CALL_JOB.value
    token_payload, auth_subject = authenticate_token(request)

    if token_payload.subject_type == AuthSubjectType.INTERNAL.value:
        authorize_internal_token(token_payload, scope, job_model.name, job_model.version, endpoint)
    else:
        assert auth_subject is not None
        authorize_resource_access(auth_subject, job_model.name, job_model.version, scope, endpoint)
