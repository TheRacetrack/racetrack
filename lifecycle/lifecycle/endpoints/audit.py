from fastapi import APIRouter, Request

from lifecycle.fatman.audit import read_audit_log_user_events
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

    @api.get('/audit/user_events/fatman/{fatman_name}')
    def _get_audit_user_events_fatman_endpoint(fatman_name: str, request: Request):
        """List all audit log events for the current user and fatman family"""
        check_auth(request, subject_types=[AuthSubjectType.USER])
        username = get_username_from_token(request)
        return read_audit_log_user_events(username, fatman_name)

    @api.get('/audit/user_events/fatman/{fatman_name}/{fatman_version}')
    def _get_audit_user_events_fatman_version_endpoint(fatman_name: str, fatman_version: str, request: Request):
        """List all audit log events for the current user and particular fatman"""
        check_auth(request, subject_types=[AuthSubjectType.USER])
        username = get_username_from_token(request)
        return read_audit_log_user_events(username, fatman_name, fatman_version)

    @api.get('/audit/events')
    def _get_audit_events(request: Request):
        """List all audit log events"""
        check_auth(request)
        return read_audit_log_user_events(None)

    @api.get('/audit/events/fatman/{fatman_name}')
    def _get_audit_events_fatman(request: Request, fatman_name: str):
        """List all audit log events for the fatman family"""
        check_auth(request)
        return read_audit_log_user_events(None, fatman_name)

    @api.get('/audit/events/fatman/{fatman_name}/{fatman_version}')
    def _get_audit_events_fatman_version(request: Request, fatman_name: str, fatman_version: str):
        """List all audit log events for the particular fatman"""
        check_auth(request)
        return read_audit_log_user_events(None, fatman_name, fatman_version)
