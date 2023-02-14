import os

import backoff
import pytest

from racetrack_commons.dir import project_root
from racetrack_client.client.deploy import send_deploy_request
from racetrack_client.client_config.auth import set_user_auth
from racetrack_client.client_config.client_config import ClientConfig
from racetrack_client.utils.request import Requests, ResponseError
from racetrack_client.utils.auth import RT_AUTH_HEADER, is_auth_required
from racetrack_commons.entities.dto import EscDto
from racetrack_commons.entities.esc_client import EscRegistryClient
from racetrack_commons.entities.job_client import JobRegistryClient

from e2e.utils import ADMIN_AUTH_TOKEN, INTERNAL_AUTH_TOKEN, _configure_env, _create_esc, _delete_workload, _wait_for_components, _install_plugin

TEST_SUITE = os.getenv('TEST_SUITE')
suite_auth = pytest.mark.skipif(
    TEST_SUITE != 'auth' and TEST_SUITE != 'full', reason='TEST_SUITE value != auth,full'
)


@suite_auth
def test_deploy_job_chain():
    _configure_env()
    _wait_for_components()

    _install_plugin('github.com/TheRacetrack/plugin-python-job-type')
    esc = _create_esc()

    _delete_workload('adder')
    _deploy_and_verify('sample/python-class', 'adder', esc)
    _verify_deployed_job_adder_response('adder', ADMIN_AUTH_TOKEN)

    _delete_workload('python-chain')
    _deploy_and_verify('sample/python-chain', 'python-chain', esc)

    _make_wrongly_authenticated_request('adder')


@suite_auth
def test_deploy_unauthenticated():
    _configure_env()
    _wait_for_components()

    _install_plugin('github.com/TheRacetrack/plugin-python-job-type')
    lifecycle_url = os.environ['LIFECYCLE_URL']
    expect_fail = is_auth_required(lifecycle_url)
    sample_path = 'sample/python-class'

    print(f'Deploying unauthenticated {sample_path} job...')
    workdir = str(project_root() / sample_path)
    config = ClientConfig()
    set_user_auth(config, lifecycle_url, 'invalid')

    if expect_fail:
        with pytest.raises(ResponseError):
            send_deploy_request(workdir, lifecycle_url=lifecycle_url, client_config=config, force=True)
    else:
        send_deploy_request(workdir, lifecycle_url=lifecycle_url, client_config=config, force=True)


@suite_auth
def test_deploy_wrong_authentication():
    _configure_env()
    _wait_for_components()

    _install_plugin('github.com/TheRacetrack/plugin-python-job-type')
    lifecycle_url = os.environ['LIFECYCLE_URL']
    sample_path = 'sample/python-class'
    print(f'Deploying with wrong authentication {sample_path} job...')
    expect_fail = is_auth_required(lifecycle_url)

    workdir = str(project_root() / sample_path)
    config = ClientConfig()
    # wrong token
    user_auth = "eyJ1c2VybmFtZSI6ICJmb28iLCAidG9rZW4iOiAiOGJjMDkzMGEtNTA2Mi00MWFiLWE4MWQtNDVhNjg0OWIyYjg4In1="
    set_user_auth(config, lifecycle_url, user_auth)

    if expect_fail:
        with pytest.raises(ResponseError):
            send_deploy_request(workdir, lifecycle_url=lifecycle_url, client_config=config, force=True)
    else:
        send_deploy_request(workdir, lifecycle_url=lifecycle_url, client_config=config, force=True)


def _deploy(sample_path: str):
    lifecycle_url = os.environ['LIFECYCLE_URL']
    config = ClientConfig()
    set_user_auth(config, lifecycle_url, ADMIN_AUTH_TOKEN)
    print(f'Deploying {sample_path} job...')
    workdir = str(project_root() / sample_path)
    send_deploy_request(workdir, lifecycle_url=lifecycle_url, client_config=config, force=True)


def _deploy_and_verify(sample_path: str, job_name: str, esc: EscDto):
    _deploy(sample_path)

    print(f'Allowing a job {job_name} to ESC...')
    erc = EscRegistryClient(auth_token=INTERNAL_AUTH_TOKEN)
    erc.esc_allow_job(esc_id=esc.id, job_name=job_name)
    esc_token = erc.get_esc_auth_token(esc.id)

    if job_name == 'adder':
        _verify_deployed_job_adder_response(job_name, esc_token)
    elif job_name == 'python-chain':
        frc = JobRegistryClient(auth_token=INTERNAL_AUTH_TOKEN)
        frc.job_allow_job('python-chain', 'adder')
        _verify_deployed_job_chain_adder_reponse(job_name, esc_token)

    _verify_job_logs(job_name, ADMIN_AUTH_TOKEN)


@backoff.on_exception(backoff.fibo, AssertionError, max_value=3, max_time=60, jitter=None)
def _verify_deployed_job_adder_response(job_name: str, auth_token: str):
    print(f'Verifying {job_name} job response...')
    pub_url = os.environ['PUB_URL']
    url = f'{pub_url}/job/{job_name}/latest/api/v1/perform'
    headers = {RT_AUTH_HEADER: auth_token}
    r = Requests.post(url, json={'numbers': [40, 2]}, headers=headers)
    assert r.ok, f'Job response: {r.status_code} {r.status_reason} for url {r.url}, content: {str(r.content)}'
    output = r.json()
    assert output == 42, 'Unexpected output returned by Job'


@backoff.on_exception(backoff.fibo, AssertionError, max_value=3, max_time=30, jitter=None)
def _verify_deployed_job_chain_adder_reponse(job_name: str, auth_token: str):
    print(f'Verifying {job_name} job response...')
    pub_url = os.environ['PUB_URL']
    url = f'{pub_url}/job/{job_name}/latest/api/v1/perform'
    r = Requests.post(url, json={'numbers': [40, 2.7]}, headers={RT_AUTH_HEADER: auth_token})
    assert r.ok, f'Job response: {r.status_code} {r.status_reason} for url {r.url}, content: {str(r.content)}'
    output = r.json()
    assert output == 43, 'Unexpected output returned by Job'


@backoff.on_exception(backoff.fibo, ResponseError, max_value=3, max_time=60, jitter=None)
def _verify_job_logs(job_name: str, user_auth: str):
    print(f'Verifying {job_name} logs...')
    frc = JobRegistryClient(auth_token=user_auth)
    logs = frc.get_runtime_logs(job_name, 'latest')
    assert len(logs) > 1, 'Unexpected short log from Job'


def _make_wrongly_authenticated_request(job_name: str):
    print(f'Verifying requests without authentication to {job_name}...')
    pub_url = os.environ['PUB_URL']
    url = f'{pub_url}/job/{job_name}/latest/api/v1/perform'

    lifecycle_url = os.environ['LIFECYCLE_URL']
    auth_required = is_auth_required(lifecycle_url)

    # wrong auth token value
    r = Requests.post(url, json={'numbers': [40, 2]}, headers={RT_AUTH_HEADER: 'MrNobody'})
    if auth_required:
        assert r.status_code == 401
    else:
        assert r.status_code == 200

    # lack of auth token
    r = Requests.post(url, json={'numbers': [40, 2]}, headers={})
    if auth_required:
        assert r.status_code == 401
    else:
        assert r.status_code == 200
