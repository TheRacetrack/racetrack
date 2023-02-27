from urllib.parse import quote_plus

from racetrack_client.utils.datamodel import parse_dict_datamodel
from racetrack_commons.entities.dto import UserProfileDto
from racetrack_commons.entities.lifecycle_client import LifecycleClient


class UserRegistryClient:
    def __init__(self, auth_token: str):
        self.lc_client = LifecycleClient(auth_token)

    def get_user_profile(self, username: str) -> UserProfileDto:
        username_encoded = quote_plus(username)
        response = self.lc_client.request_dict('get', f'/api/v1/users/{username_encoded}/profile')
        return parse_dict_datamodel(response, UserProfileDto)

    def init_user_profile(self, username: str) -> UserProfileDto:
        username_encoded = quote_plus(username)
        response = self.lc_client.request_dict('post', f'/api/v1/users/{username_encoded}/profile')
        return parse_dict_datamodel(response, UserProfileDto)

    def regen_user_token(self, username: str) -> UserProfileDto:
        username_encoded = quote_plus(username)
        response = self.lc_client.request('post', f'/api/v1/auth/token/user/{username_encoded}/regenerate')
