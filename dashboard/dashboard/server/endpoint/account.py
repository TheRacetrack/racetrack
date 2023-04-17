from typing import Annotated

from fastapi import Request, FastAPI, Form
from fastapi.responses import JSONResponse, Response

from racetrack_client.log.context_error import ContextError, unwrap
from racetrack_client.log.exception import log_exception
from racetrack_client.utils.auth import RT_AUTH_HEADER
from racetrack_commons.auth.auth import UnauthorizedError
from racetrack_commons.auth.token import decode_jwt
from racetrack_commons.entities.dto import UserProfileDto
from racetrack_commons.entities.users_client import UserAccountClient
from dashboard.cookie import set_auth_token_cookie, delete_auth_cookie


def setup_account_endpoints(app: FastAPI):

    @app.post("/api/accounts/login")
    def _login(username: Annotated[str, Form()], password: Annotated[str, Form()]):
        try:
            user_profile: UserProfileDto = UserAccountClient().login_user(username, password)
            response = JSONResponse(user_profile.dict())
            set_auth_token_cookie(user_profile.token, response)
            return response
        
        except Exception as e:
            log_exception(ContextError('Login failed', e))
            root_exception = unwrap(e)
            raise UnauthorizedError(str(root_exception))

    @app.get("/api/accounts/logout")
    def _logout():
        response = Response()
        delete_auth_cookie(response)
        return response
    
    @app.post("/api/accounts/register")
    def _register(
        username: Annotated[str, Form()],
        password1: Annotated[str, Form()],
        password2: Annotated[str, Form()],
    ) -> dict:
        if "@" not in username:
            raise RuntimeError("You have to pass email as username")
        if not password1:
            raise RuntimeError("Password cannot be empty")
        if password1 != password2:
            raise RuntimeError("Passwords do not match")

        UserAccountClient().register_user(username, password1)

        return {
            'success': f'Your account "{username}" have been registered. Now wait till Racetrack admin activates your account.',
        }
    
    @app.post("/api/accounts/change_password")
    def _change_password(
        request: Request,
        old_password: Annotated[str, Form()],
        new_password1: Annotated[str, Form()],
        new_password2: Annotated[str, Form()],
    ):
        if not old_password or not new_password1:
            raise RuntimeError("Password cannot be empty")
        if new_password1 != new_password2:
            raise RuntimeError("Passwords do not match")

        user_client = UserAccountClient(auth_token=get_auth_token(request))
        user_client.change_password(old_password, new_password1)

        return {
            'success': f'Your password has been changed.',
        }


def get_auth_token(request: Request) -> str:
    auth_token = request.headers.get(RT_AUTH_HEADER)
    if not auth_token:
        raise UnauthorizedError(f'Auth token not found in a header {RT_AUTH_HEADER}')
    decode_jwt(auth_token)
    return auth_token
