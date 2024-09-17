from django.contrib.auth.models import User
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from lifecycle.auth.authenticate import get_username_from_token
from lifecycle.auth.check import check_auth
from lifecycle.auth.cookie import set_auth_token_cookie, delete_auth_cookie
from lifecycle.auth.subject import get_auth_token_by_subject
from lifecycle.auth.users import authenticate_username_with_password, register_user_account
from lifecycle.auth.users import change_user_password
from racetrack_client.log.errors import ValidationError
from racetrack_commons.auth.auth import AuthSubjectType
from racetrack_commons.entities.dto import UserProfileDto


def setup_user_endpoints(api: APIRouter):

    class UserCredentialsModel(BaseModel):
        username: str
        password: str

    class ChangePasswordModel(BaseModel):
        old_password: str
        new_password: str

    @api.get('/users/validate_user_auth')
    def _validate_user_auth(request: Request) -> UserProfileDto:
        """Validate auth token and return corresponding username"""
        auth_subject = check_auth(request, subject_types=[AuthSubjectType.USER])
        assert auth_subject is not None
        assert auth_subject.user_id is not None
        username = get_username_from_token(request)
        user: User = auth_subject.user
        auth_token = get_auth_token_by_subject(auth_subject)
        return UserProfileDto(
            username=username,
            token=auth_token.token,
            is_staff=user.is_staff,
        )

    @api.post('/users/login')
    def _login_user_account(payload: UserCredentialsModel) -> JSONResponse:
        """Validate username and password and return auth token and user data"""
        user, auth_subject, auth_token = authenticate_username_with_password(payload.username, payload.password)
        user_profile = UserProfileDto(
            username=user.username,
            token=auth_token.token,
            is_staff=user.is_staff,
        )
        response = JSONResponse(user_profile.model_dump())
        set_auth_token_cookie(user_profile.token, response)
        return response

    @api.get('/users/logout')
    def _logout() -> Response:
        response = Response()
        delete_auth_cookie(response)
        return response

    @api.post('/users/register')
    def _register_user_account(payload: UserCredentialsModel):
        if "@" not in payload.username:
            raise ValidationError("You have to pass email as username")
        if not payload.password:
            raise ValidationError("Password cannot be empty")

        register_user_account(payload.username, payload.password)

    @api.put('/users/change_password')
    def _change_user_password(payload: ChangePasswordModel, request: Request):
        if not payload.new_password:
            raise ValidationError("Password cannot be empty")

        check_auth(request)
        username = get_username_from_token(request)
        change_user_password(username, payload.old_password, payload.new_password)
