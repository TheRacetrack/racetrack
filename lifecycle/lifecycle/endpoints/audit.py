from fastapi import APIRouter, Request

from lifecycle.job.audit import read_audit_log_user_events
from lifecycle.config import Config
from lifecycle.auth.authenticate import get_username_from_token
from lifecycle.auth.check import check_auth
from racetrack_commons.auth.auth import AuthSubjectType


def setup_audit_endpoints(api: APIRouter, config: Config):

    @api.get('/audit/user_events')
    def _get_autdit_user_events(request: Request):
        """List all audit log events for the current user"""
        check_auth(request, subject_types=[AuthSubjectType.USER])
        username = get_username_from_token(request)
        return read_audit_log_user_events(username)

    @api.get('/audit/user_events/job/{job.name}')
    def _get_audit_user_events_job_endpoint(job.name: str, request: Request):
        """List all audit log events for the current user and job family"""
        check_auth(request, subject_types=[AuthSubjectType.USER])
        username = get_username_from_token(request)
        return read_audit_log_user_events(username, job.name)

    @api.get('/audit/user_events/job/{job.name}/{job.version}')
    def _get_audit_user_events_job.version_endpoint(job.name: str, job.version: str, request: Request):
        """List all audit log events for the current user and particular job"""
        check_auth(request, subject_types=[AuthSubjectType.USER])
        username = get_username_from_token(request)
        return read_audit_log_user_events(username, job.name, job.version)

    @api.get('/audit/events')
    def _get_audit_events(request: Request):
        """List all audit log events"""
        check_auth(request)
        return read_audit_log_user_events(None)

    @api.get('/audit/events/job/{job.name}')
    def _get_audit_events_job(request: Request, job.name: str):
        """List all audit log events for the job family"""
        check_auth(request)
        return read_audit_log_user_events(None, job.name)

    @api.get('/audit/events/job/{job.name}/{job.version}')
    def _get_audit_events_job.version(request: Request, job.name: str, job.version: str):
        """List all audit log events for the particular job"""
        check_auth(request)
        return read_audit_log_user_events(None, job.name, job.version)
