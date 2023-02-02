from typing import Dict, Optional

import backoff
from racetrack_client.utils.shell import CommandError, shell
from racetrack_client.utils.time import datetime_to_timestamp, now

from racetrack_client.client.deploy import DEPLOYMENT_TIMEOUT_SECS, BuildContextMethod, DeploymentError, get_build_context, get_deploy_request_payload, get_git_credentials
from racetrack_client.client_config.io import load_client_config
from racetrack_client.manifest.validate import load_validated_manifest
from racetrack_client.log.logs import get_logger
from racetrack_client.client.env import hide_env_vars, merge_env_vars, read_secret_vars
from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.request import parse_response_object, Requests

logger = get_logger(__name__)

JOB_INTERNAL_PORT = 7000  # Job listening port seen from inside the container


def run_job_locally(
    workdir: str, 
    lifecycle_url: str, 
    build_context_method: BuildContextMethod = BuildContextMethod.default,
    port: Optional[int] = None,
):
    client_config = load_client_config()
    manifest = load_validated_manifest(workdir)

    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)

    logger.info(f'building workspace "{workdir}" (job {manifest.name} v{manifest.version}) by {lifecycle_url}')

    build_context = get_build_context(lifecycle_url, workdir, manifest, build_context_method)
    git_credentials = get_git_credentials(manifest, client_config)
    secret_vars = read_secret_vars(workdir, manifest)

    # see `lifecycle.endpoints.deploy::setup_deploy_endpoints::BuildEndpoint` for server-side implementation
    r = Requests.post(
        f'{lifecycle_url}/api/v1/build',
        json=get_deploy_request_payload(manifest, git_credentials, secret_vars, build_context, False),
        headers=get_auth_request_headers(user_auth),
    )
    response = parse_response_object(r, 'Lifecycle building error')
    deployment_id = response["id"]
    logger.info(f'job buidling requested: {deployment_id}')

    try:
        job_image_name = _wait_for_building_result(lifecycle_url, deployment_id, user_auth)
    except Exception as e:
        raise DeploymentError(e)

    logger.info(f'Job image "{manifest.name}" v{manifest.version} has been built.')

    try:
        shell(f'docker', print_stdout=False)
    except CommandError as e:
        raise RuntimeError('Docker is not installed in the system') from e

    logger.info(f'Pulling image {job_image_name}')
    docker_registry = extract_docker_registry(job_image_name)
    logger.info(f'Logging in to Docker registry: {docker_registry}')
    shell(f'docker login {docker_registry}', read_bytes=True)

    shell(f'docker pull {job_image_name}')

    port = port or 7000
    container_name = f'local-job-{manifest.name}-v-{manifest.version}'.replace('.', '-')

    deployment_timestamp = datetime_to_timestamp(now())
    runtime_env_vars = merge_env_vars(manifest.runtime_env, secret_vars.runtime_env)
    build_env_vars = merge_env_vars(manifest.build_env, secret_vars.build_env)
    runtime_env_vars = hide_env_vars(runtime_env_vars, build_env_vars)
    common_env_vars: Dict[str, str] = {
        'JOB_NAME': manifest.name,
        'JOB_DEPLOYMENT_TIMESTAMP': str(deployment_timestamp),
    }
    runtime_env_vars = merge_env_vars(runtime_env_vars, common_env_vars)
    env_vars_cmd = ' '.join([f'--env {env_name}="{env_val}"' for env_name, env_val in runtime_env_vars.items()])

    job_url = f'http://127.0.0.1:{port}/pub/job/{manifest.name}/{manifest.version}/'
    logger.info(f'Running job "{manifest.name}" v{manifest.version} locally. '
                f'Check out {job_url} to access your job. CTRL-C to stop.')
    try:
        shell(
            f'docker run --rm -it'
            f' --name {container_name}'
            f' -p {port}:{JOB_INTERNAL_PORT}'
            f' {env_vars_cmd}'
            f' --label job-name={manifest.name}'
            f' --label job-version={manifest.version}'
            f' {job_image_name}'
        )
    except CommandError as e:
        if e.returncode == 130:  # Container terminated by Control-C
            return
        raise e


@backoff.on_exception(
    backoff.fibo, TimeoutError, max_value=5, max_time=DEPLOYMENT_TIMEOUT_SECS, jitter=None, logger=None
)
def _wait_for_building_result(lifecycle_url: str, deployment_id: str, user_auth: str) -> str:
    # see `lifecycle.endpoints.deploy::setup_deploy_endpoints::DeployIdEndpoint` for server-side implementation
    r = Requests.get(
        f'{lifecycle_url}/api/v1/deploy/{deployment_id}',
        headers=get_auth_request_headers(user_auth),
    )
    response = parse_response_object(r, 'Lifecycle building status')
    status = response['status'].lower()
    if status == 'failed':
        raise RuntimeError(response['error'])
    if status == 'done':
        return response['image_name']

    phase = response.get('phase')
    if phase:
        logger.info(f'building in progress: {phase}...')
    else:
        logger.info(f'building in progress...')
    raise TimeoutError('Building timeout error')


def extract_docker_registry(job_image_name: str) -> str:
    return job_image_name.split('/')[0]
