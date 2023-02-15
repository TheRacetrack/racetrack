from typing import Callable, Dict

import backoff

from racetrack_client.utils.request import Requests, RequestError, Response


def check_until_job_is_operational(
    base_url: str,
    deployment_timestamp: int = 0,
    on_job_alive: Callable = None,
):
    """
    Check liveness and readiness of a Job in a multi-stage manner:
    - wait for Job to accept HTTP connections, wait for k8s/docker to bring up the pod/container
    - check liveness endpoint if there was a critical error
    - check readiness periodically until Job is initialized
    :param base_url: url of Job home page
    :param deployment_timestamp: timestamp of deployment to verify if the running version is really the expected one
    If set to zero, checking version is skipped.
    :param on_job_alive: handler called when Job is live, but not ready yet
    (server running already, but still initializing)
    :raise RuntimeError in case of failure
    """
    response = wait_until_job_is_alive(base_url, deployment_timestamp)
    _validate_live_response(response)
    if on_job_alive:
        on_job_alive()
    wait_until_job_is_ready(base_url)


# this can have long timeout since any potential malfunction in here is not related to a model/entrypoint
# but the cluster errors that shouldn't happen usually
@backoff.on_exception(backoff.fibo, RuntimeError, max_value=3, max_time=360, jitter=None, logger=None)
def wait_until_job_is_alive(base_url: str, expected_deployment_timestamp: int) -> Response:
    """Wait until Job resource (pod or container) is up. This catches internal cluster errors"""
    try:
        response = Requests.get(f'{base_url}/live', timeout=3)
    except RequestError as e:
        raise RuntimeError(f"Cluster error: can't reach Job: {e}")

    # prevent from getting responses from the old, dying pod. Ensure new Job responds to probes
    if expected_deployment_timestamp and 'application/json' in response.headers['content-type']:
        result: Dict = response.json()
        current_deployment_timestamp = int(result.get('deployment_timestamp') or 0)
        if current_deployment_timestamp != expected_deployment_timestamp:
            raise RuntimeError("Cluster error: can't reach newer Job")

    return response


@backoff.on_exception(backoff.fibo, TimeoutError, max_value=3, max_time=10 * 60, jitter=None, logger=None)
def wait_until_job_is_ready(base_url: str):
    response = Requests.get(f'{base_url}/ready', timeout=3)
    if response.status_code == 200:
        return
    if response.status_code == 404:
        raise RuntimeError('Job health error: readiness endpoint not found')

    response = Requests.get(f'{base_url}/live', timeout=3)
    _validate_live_response(response)

    raise TimeoutError('Job initialization timed out')


def _validate_live_response(response: Response):
    """Check liveness probe and report error immediately once Job has crashed during startup"""
    if response.status_code == 200:
        return
    if response.status_code == 404:
        raise RuntimeError('Job health error: liveness endpoint not found')

    if 'application/json' in response.headers['content-type']:
        result = response.json()
        if 'error' in result:
            raise RuntimeError(f'Job initialization error: {result.get("error")}')

    raise RuntimeError(f'Job liveness error: {response.status_code} {response.status_reason}')


def quick_check_job_condition(base_url: str):
    """
    Quick check (1 attempt) if Job is live and ready.
    :param base_url: url of Job home page
    :raise RuntimeError in case of failure
    """
    try:
        response = Requests.get(f'{base_url}/live', timeout=3)
    except RequestError as e:
        raise RuntimeError(f"Cluster error: can't reach Job: {e}")
    _validate_live_response(response)

    try:
        response = Requests.get(f'{base_url}/ready', timeout=3)
    except RequestError as e:
        raise RuntimeError(f"Cluster error: can't reach Job: {e}")
    if response.status_code == 200:
        return
    if response.status_code == 404:
        raise RuntimeError('Job health error: readiness endpoint not found')
    raise RuntimeError('Job is still initializing')
