import json
import os
import urllib3

from locust import HttpUser, task, tag
from dotenv import load_dotenv

from racetrack_commons.entities.esc_client import EscRegistryClient
from racetrack_commons.entities.dto import EscDto


def _create_esc(job_name: str, esc_name: str, admin_auth_token: str) -> str:
    print('Creating ESC...')
    erc = EscRegistryClient(auth_token=admin_auth_token)
    esc: EscDto = erc.create_esc(esc_name)
    erc.esc_allow_job(esc_id=esc.id, job_name=job_name)
    esc_token = erc.get_esc_auth_token(esc.id)
    return esc_token


class JobStressUser(HttpUser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        env_file = os.environ.get('ENV_FILE', '.env')
        print(f"Using configuration from env file: {env_file}")
        load_dotenv(env_file)

        self.base_url = os.environ['base_url']
        print(f"Using base URL: {self.base_url}")

        job_name = os.environ['job_name']
        job_version = os.environ['job_version']
        self.url = f"{self.base_url}/pub/job/{job_name}/{job_version}"
        print(f"url to hit: {self.url}")

        is_localhost = '://localhost' in self.base_url
        esc_name = os.environ.get('create_esc')
        if is_localhost and esc_name:
            admin_auth_token = os.environ.get('admin_auth_token')
            auth_token = _create_esc(job_name, esc_name, admin_auth_token)
        else:
            auth_token = os.environ.get('auth_token')

        self.headers = urllib3.make_headers()
        
        if auth_token:
            self.headers["X-Racetrack-Auth"] = auth_token
        else:
            print('WARNING: no auth_token')

        self.headers["Content-Type"] = "application/json"
        self.headers["accept"] = "application/json"

        payload_str = os.environ.get('payload')
        self.payload = json.loads(payload_str) if payload_str else None

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
        self.client.post(url=f"{self.url}/api/v1/perform", headers=self.headers, json=self.payload)

    @tag('auth_fail')
    @task(1)
    def test_perform_auth_fail(self):
        headers = urllib3.make_headers()
        headers["Content-Type"] = "application/json"
        headers["X-Racetrack-Esc-Auth"] = "foo"
        with self.client.post(url=f"{self.url}/api/v1/perform", headers=headers, json={'numbers': [40, 2]}, catch_response=True) as resp:
            resp.success()

    @tag('lifecycle_metrics')
    @task(1)
    def test_lifecycle_metrics(self):
        self.client.get(url=self.base_url, headers=self.headers)
