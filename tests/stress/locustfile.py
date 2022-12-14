import os
import urllib3

from locust import HttpUser, task, tag
from dotenv import load_dotenv

from racetrack_commons.entities.esc_client import EscRegistryClient
from racetrack_commons.entities.dto import EscDto


def _create_esc(fatman_name: str, esc_name: str, admin_auth_token: str) -> str:
    print('Creating ESC...')
    erc = EscRegistryClient(auth_token=admin_auth_token)
    esc: EscDto = erc.create_esc(esc_name)
    erc.esc_allow_fatman(esc_id=esc.id, fatman_name=fatman_name)
    esc_token = erc.get_esc_auth_token(esc.id)
    return esc_token


class FatmanStressUser(HttpUser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        load_dotenv()

        test_env = os.environ.get('test_env')
        print(f"Using test_env: {test_env}")

        is_localhost = True
        if test_env == 'kind':
            self.base_url = 'http://localhost:7005/pub'
        elif test_env == 'compose':
            self.base_url = 'http://localhost:7105/pub'
        else:
            self.base_url = os.environ['external_pub_url']
            is_localhost = False

        fatman_name = os.environ['fatman_name']
        fatman_version = os.environ['fatman_version']
        self.url = f"{self.base_url}/fatman/{fatman_name}/{fatman_version}"
        print(f"url to hit: {self.url}")

        esc_name = os.environ.get('create_esc')
        if is_localhost and esc_name:
            admin_auth_token = os.environ.get('admin_auth_token')
            auth_token = _create_esc(fatman_name, esc_name, admin_auth_token)
        else:
            auth_token = os.environ['auth_token']

        self.headers = urllib3.make_headers()
        
        if auth_token:
            self.headers["X-Racetrack-Auth"] = auth_token
            self.headers["X-Racetrack-User-Auth"] = auth_token
        else:
            raise ValueError('use auth_token')

        self.headers["Content-Type"] = "application/json"
        self.headers["accept"] = "application/json"

    @tag('live')
    @task(5)  # number in task indicates weight, higher means more calls
    def test_live(self):
        self.client.get(url=f"{self.url}/live", headers=self.headers)

    @tag('health')
    @task(5)
    def test_health(self):
        self.client.get(url=f"{self.url}/health", headers=self.headers)

    @tag('perform')
    @task(5)
    def test_perform(self):
        self.client.post(url=f"{self.url}/api/v1/perform", headers=self.headers, json={
            "mode": "cpu",
            "t": 3,
        })

    @task(1)
    def test_perform_auth_fail(self):
        headers = urllib3.make_headers()
        headers["Content-Type"] = "application/json"
        headers["X-Racetrack-Esc-Auth"] = "foo"
        with self.client.post(url=f"{self.url}/api/v1/perform", headers=headers, json={'numbers': [40, 2]}, catch_response=True) as resp:
            resp.success()
