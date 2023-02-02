import os
import random

import backoff

from racetrack_client.log.context_error import ContextError
from racetrack_client.utils.request import ResponseError, Requests, RequestError
from racetrack_commons.dir import project_root
from racetrack_commons.entities.dto import EscDto
from racetrack_commons.entities.esc_client import EscRegistryClient
from racetrack_commons.entities.job_client import JobRegistryClient
from racetrack_client.utils.auth import RT_AUTH_HEADER
from racetrack_client.client_config.auth import set_user_auth
from racetrack_client.client_config.client_config import ClientConfig
from racetrack_client.client.deploy import send_deploy_request
from racetrack_client.plugin.install import install_plugin

INTERNAL_AUTH_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZWVkIjoiMzIyZTA4MDQtMzQyYi00MjQ5LWIzZTktNmY1MGVjZTZhYTRhIiwic3ViamVjdCI6ImUyZV90ZXN0Iiwic3ViamVjdF90eXBlIjoiaW50ZXJuYWwiLCJzY29wZXMiOlsiZnVsbF9hY2Nlc3MiXX0.Tt_o4z22cRNfqBQ3EX0mA2gNKSvv4m5beganNRhheos'
ADMIN_AUTH_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI'


def _configure_env() -> str:
    environment = os.environ.get('TEST_ENV', 'kind')
    print(f'Running jobs test on {environment} environment...')
    if environment == 'kind':
        os.environ['LIFECYCLE_URL'] = 'http://localhost:7002/lifecycle'
        os.environ['IMAGE_BUILDER_URL'] = 'http://localhost:7001'
        os.environ['PUB_URL'] = 'http://localhost:7005/pub'
    elif environment == 'docker':
        os.environ['LIFECYCLE_URL'] = 'http://localhost:7102/lifecycle'
        os.environ['IMAGE_BUILDER_URL'] = 'http://localhost:7101'
        os.environ['PUB_URL'] = 'http://localhost:7105/pub'
    elif environment == 'localhost':
        os.environ['LIFECYCLE_URL'] = 'http://localhost:7202/lifecycle'
        os.environ['IMAGE_BUILDER_URL'] = 'http://localhost:7201'
        os.environ['PUB_URL'] = 'http://localhost:7205/pub'
    elif environment == 'kubernetes':
        test_host = os.environ['TEST_HOST']
        os.environ['LIFECYCLE_URL'] = test_host + '/lifecycle'
        os.environ['IMAGE_BUILDER_URL'] = ''
        os.environ['PUB_URL'] = test_host + '/pub'
    return environment


def _wait_for_components():
    print('Waiting for Lifecycle to be ready...')
    _wait_for_lifecycle_ready()
    print('Waiting for image-builder to be ready...')
    _wait_for_image_builder_ready()


@backoff.on_exception(backoff.fibo, RequestError, max_value=3, max_time=150, jitter=None)
def _wait_for_lifecycle_ready():
    lifecycle_url = os.environ['LIFECYCLE_URL']
    Requests.get(f'{lifecycle_url}/ready').raise_for_status()


@backoff.on_exception(backoff.fibo, RequestError, max_value=3, max_time=60, jitter=None)
def _wait_for_image_builder_ready():
    image_builder_url = os.environ['IMAGE_BUILDER_URL']
    if image_builder_url != '':
        Requests.get(f'{image_builder_url}/health').raise_for_status()


def _delete_workload(job_name: str):
    print(f'Deleting remnant workloads of {job_name}...')
    try:
        frc = JobRegistryClient(auth_token=ADMIN_AUTH_TOKEN)
        frc.delete_deployed_job(job_name, job_version='0.0.1')
    except ResponseError as e:
        if e.status_code not in {200, 404}:
            raise ContextError('deleting previous workloads') from e


def _create_esc() -> EscDto:
    print('Creating ESC...')
    try:
        erc = EscRegistryClient(auth_token=ADMIN_AUTH_TOKEN)
        name = random.choice(['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank'])
        esc: EscDto = erc.create_esc(name)
        return esc
    except ResponseError as e:
        if e.status_code not in {200, 409}:  # created or already exists
            raise ContextError('creating ESC') from e

def _deploy_and_verify(sample_path: str, job_name: str, esc: EscDto):
    _deploy(sample_path)

    print(f'Allowing a job {job_name} to ESC...')
    erc = EscRegistryClient(auth_token=INTERNAL_AUTH_TOKEN)
    erc.esc_allow_job(esc_id=esc.id, job_name=job_name)
    esc_token = erc.get_esc_auth_token(esc.id)

    if job_name == 'adder':
        _verify_deployed_job_adder_response(job_name, esc_token)

    _verify_job_logs(job_name, ADMIN_AUTH_TOKEN)


def _deploy(sample_path: str):
    lifecycle_url = os.environ['LIFECYCLE_URL']
    config = ClientConfig()
    set_user_auth(config, lifecycle_url, ADMIN_AUTH_TOKEN)
    print(f'Deploying {sample_path} job...')
    workdir = str(project_root() / sample_path)
    send_deploy_request(workdir, lifecycle_url=lifecycle_url, client_config=config, force=True)


@backoff.on_exception(backoff.fibo, AssertionError, max_value=3, max_time=60, jitter=None)
def _verify_deployed_job_adder_response(job_name: str, auth_token: str):
    print(f'Verifying {job_name} job response...')
    pub_url = os.environ['PUB_URL']
    url = f'{pub_url}/job/{job_name}/latest/api/v1/perform'

    headers = {}
    if auth_token:
        headers[RT_AUTH_HEADER] = auth_token

    r = Requests.post(url, json={'numbers': [40, 2]}, headers=headers)
    assert r.ok, f'Job response: {r.status_code} {r.status_reason} for url {r.url}, content: {str(r.content)}'
    output = r.json()
    assert output == 42, 'Unexpected output returned by Job'


@backoff.on_exception(backoff.fibo, ResponseError, max_value=3, max_time=60, jitter=None)
def _verify_job_logs(job_name: str, user_auth: str):
    print(f'Verifying {job_name} logs...')
    frc = JobRegistryClient(auth_token=user_auth)
    logs = frc.get_runtime_logs(job_name, 'latest')
    assert len(logs) > 1, 'Unexpected short log from Job'


def _install_plugin(plugin_uri: str):
    lifecycle_url = os.environ['LIFECYCLE_URL']
    client_config = ClientConfig()
    set_user_auth(client_config, lifecycle_url, ADMIN_AUTH_TOKEN)
    print(f'Installing plugin {plugin_uri}...')
    install_plugin(plugin_uri, lifecycle_url, client_config)
