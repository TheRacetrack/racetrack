from racetrack_client.utils.datamodel import parse_dict_datamodel
from racetrack_commons.entities.dto import UserProfileDto
from racetrack_commons.entities.lifecycle_client import LifecycleClient


class UserAccountClient:
    def __init__(self, auth_token: str = ''):
        self.lc_client = LifecycleClient(auth_token)

    def register_user(self, username: str, password: str):
        self.lc_client.request('post', f'/api/v1/users/register',
                               json={username: username, password: password})

    def login_user(self, username: str, password: str) -> UserProfileDto:
        response = self.lc_client.request_dict('post', f'/api/v1/users/login',
                                               json={username: username, password: password})
        return parse_dict_datamodel(response, UserProfileDto)

    def validate_token(self) -> UserProfileDto:
        response = self.lc_client.request_dict('get', f'/api/v1/users/validate_user_auth')
        return parse_dict_datamodel(response, UserProfileDto)

    def change_password(self, old_password: str, new_password: str):
        self.lc_client.request('put', f'/api/v1/users/change_password',
                               json={old_password: old_password, new_password: new_password})

    def regen_user_token(self) -> str:
        response = self.lc_client.request('post', f'/api/v1/auth/token/user/regenerate')
        return response
