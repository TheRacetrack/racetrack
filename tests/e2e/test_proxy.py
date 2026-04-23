import os
from urllib import request as urllib_request
from urllib.error import HTTPError

from racetrack_client.log.logs import configure_logs
from racetrack_client.utils.auth import RT_AUTH_HEADER
from racetrack_commons.entities.esc_client import EscRegistryClient

from e2e.utils import (
    DOCKER_PLUGIN_VERSION,
    INTERNAL_AUTH_TOKEN,
    K8S_PLUGIN_VERSION,
    PYTHON_PLUGIN_VERSION,
    _configure_env,
    _create_esc,
    _delete_workload,
    _deploy,
    _install_plugin,
    _wait_for_components,
)


class _NoRedirectHandler(urllib_request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def test_latest_version_redirect():
    configure_logs()
    environment = _configure_env()
    _wait_for_components()

    _install_plugin(f'github.com/TheRacetrack/plugin-python-job-type=={PYTHON_PLUGIN_VERSION}')
    if environment == 'docker':
        _install_plugin(f'github.com/TheRacetrack/plugin-docker-infrastructure=={DOCKER_PLUGIN_VERSION}', replace=True)
    elif environment == 'kind':
        _install_plugin(f'github.com/TheRacetrack/plugin-kubernetes-infrastructure=={K8S_PLUGIN_VERSION}', replace=True)

    esc = _create_esc()
    assert esc is not None, 'failed to create ESC'
    _delete_workload('adder')
    _deploy('sample/python-class')

    erc = EscRegistryClient(auth_token=INTERNAL_AUTH_TOKEN)
    erc.esc_allow_job(esc_id=esc.id, job_name='adder')
    esc_token = erc.get_esc_auth_token(esc.id)

    pub_url = os.environ['PUB_URL']
    url = f'{pub_url}/job/adder/latest'

    opener = urllib_request.build_opener(_NoRedirectHandler())
    req = urllib_request.Request(url, method='GET')
    req.add_header(RT_AUTH_HEADER, esc_token)

    try:
        response = opener.open(req)
        status = response.status
        location = response.headers.get('Location')
    except HTTPError as e:
        status = e.code
        location = e.headers.get('Location')

    assert 300 <= status < 400, f'expected redirect response, got {status}'
    assert location is not None, 'missing Location header'
    assert '/pub/job/adder/latest' in location, f'unexpected location, got: {location!r}'
    
