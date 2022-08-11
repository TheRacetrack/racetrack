from typing import Optional
from fastapi import APIRouter, Request

from lifecycle.auth.authenticate import get_username_from_token
from lifecycle.django.registry.database import before_db_access
from lifecycle.config import Config
from lifecycle.auth.check import check_auth
from lifecycle.server.users import read_user_profile, init_user_profile
from pydantic import BaseModel, Field
from racetrack_commons.auth.scope import AuthScope


def setup_user_endpoints(api: APIRouter, config: Config):

    class UserProfileModel(BaseModel):
        username: Optional[str] = Field(
            default=None,
            description='username',
            example='admin',
        )
        token: Optional[str] = Field(
            default=None,
            description='auth token',
            example='eyJ1c2VybmFtZSI6ICJhZG1pbiIsICJ0b2tlbiI6ICIwMjg1ZmIzZC1hNDVjLTQ5NjYtYTU5OC1mZmJiMzJiYzhkNTQifQ==',
        )

    @api.get('/users/{username}/profile', response_model=UserProfileModel)
    def _get_user_profile(username: str, request: Request):
        """Get profile of particular User"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        return read_user_profile(username)

    @api.post('/users/{username}/profile', response_model=UserProfileModel)
    def _init_user_profile(username: str, request: Request):
        """Init profile of particular User"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        before_db_access()
        return init_user_profile(username)

    @api.get('/users/validate_user_auth')
    def _validate_user_auth(request: Request):
        """Validate auth token and return corresponding username"""
        check_auth(request)
        username = get_username_from_token(request)
        return {'username': username}
