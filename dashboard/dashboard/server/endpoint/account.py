from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from racetrack_client.log.context_error import ContextError, unwrap
from racetrack_client.log.exception import log_exception
from racetrack_client.utils.auth import RT_AUTH_HEADER
from racetrack_commons.auth.auth import UnauthorizedError
from racetrack_commons.auth.token import decode_jwt
from racetrack_commons.entities.dto import UserProfileDto
from racetrack_commons.entities.users_client import UserAccountClient
from dashboard.cookie import set_auth_token_cookie, delete_auth_cookie


def setup_account_endpoints(app: FastAPI):

    class UserCredentialsModel(BaseModel):
        username: str
        password: str

    @app.post("/api/accounts/login")
    def _login(payload: UserCredentialsModel):
        try:
            user_profile: UserProfileDto = UserAccountClient().login_user(payload.username, payload.password)
            response = JSONResponse(user_profile.dict())
            set_auth_token_cookie(user_profile.token, response)
            return response
        
        except Exception as e:
            log_exception(ContextError('Login failed', e))
            raise unwrap(e)

    @app.get("/api/accounts/logout")
    def _logout():
        response = Response()
        delete_auth_cookie(response)
        return response
    
    class RegisterModel(BaseModel):
        username: str
        password1: str
        password2: str

    @app.post("/api/accounts/register")
    def _register(payload: RegisterModel) -> dict:
        if "@" not in payload.username:
            raise RuntimeError("You have to pass email as username")
        if not payload.password1:
            raise RuntimeError("Password cannot be empty")
        if payload.password1 != payload.password2:
            raise RuntimeError("Passwords do not match")

        UserAccountClient().register_user(payload.username, payload.password1)

        return {
            'success': f'Your account "{payload.username}" have been registered. Now wait till Racetrack admin activates your account.',
        }
    
    class ChangePasswordModel(BaseModel):
        old_password: str
        new_password1: str
        new_password2: str

    @app.post("/api/accounts/change_password")
    def _change_password(request: Request, payload: ChangePasswordModel):
        if not payload.old_password or not payload.new_password1:
            raise RuntimeError("Password cannot be empty")
        if payload.new_password1 != payload.new_password2:
            raise RuntimeError("Passwords do not match")

        user_client = UserAccountClient(auth_token=get_auth_token(request))
        user_client.change_password(payload.old_password, payload.new_password1)

        return {
            'success': f'Your password has been changed.',
        }


def get_auth_token(request: Request) -> str:
    auth_token = request.headers.get(RT_AUTH_HEADER)
    if not auth_token:
        raise UnauthorizedError(f'Auth token not found in a header {RT_AUTH_HEADER}')
    decode_jwt(auth_token)
    return auth_token
