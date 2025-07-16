import os
from pathlib import Path
import sys
import tempfile
from typing import List, Optional, Dict
from urllib.parse import urlsplit
import tarfile
import io
from base64 import b64encode
from enum import Enum

import backoff

from racetrack_client.client.env import read_secret_vars, SecretVars
from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.client_config import ClientConfig, Credentials
from racetrack_client.client_config.io import load_client_config
from racetrack_client.manifest import Manifest
from racetrack_client.manifest.load import get_manifest_path
from racetrack_client.manifest.merge import load_merged_manifest_dict
from racetrack_client.manifest.validate import load_validated_manifest
from racetrack_client.plugin.bundler.filename_matcher import FilenameMatcher
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.byte import format_bytes
from racetrack_client.utils.request import parse_response_object, Requests
from racetrack_client.log.logs import get_logger


logger = get_logger(__name__)

DEPLOYMENT_TIMEOUT_SECS = 60 * 60  # 1 hour


class DeploymentError(RuntimeError):
    def __init__(self, cause: BaseException):
        super().__init__()
        self.__cause__ = cause

    def __str__(self):
        return f'deployment error: {self.__cause__}'


class BuildContextMethod(str, Enum):
    local = "local"
    git = "git"
    default = "default"


def catch_piped_input():
    """Check for piped input and read it if available, avoiding indefinite blocking."""
    piped_data, file_path= None, None
    if not sys.stdin.isatty() and (piped_data := sys.stdin.read()):
        current_workdir = os.getcwd()
        with tempfile.NamedTemporaryFile(mode='w+', dir=current_workdir, delete=False) as tmp_file:
            tmp_file.write(piped_data)
            tmp_file.flush()
            file_path = tmp_file.name
    return file_path


def send_deploy_request(
    workdir: str,
    client_config: Optional[ClientConfig] = None,
    lifecycle_url: Optional[str] = None,
    force: bool = False,
    build_context_method: BuildContextMethod = BuildContextMethod.default,
    extra_vars: Optional[Dict[str, str]] = None,
    build_flags: List[str] = [],
):
    """
    Send request deploying a new Job to running Lifecycle instance
    :param workdir: directory with job.yaml manifest
    :param client_config: client configuration to use (if not the defaullt)
    :param lifecycle_url: Racetrack server's URL or alias name
    :param force: overwrite existing job without asking
    :param build_context_method: decides whether to build from local files or from git:
        local - build an image from local build context,
        git - build from git repository,
        None - apply default strategy:
            if working on local dev, local build context gets activated, otherwise git
    :param extra_vars: key-value pairs overriding manifest values
    """
    # Creates a tmp file to store the piped input. Have to try/finally to ensure it gets deleted
    try:
        # If piped input is available, use it as the workdir
        tmp_file = catch_piped_input()
        workdir = tmp_file or workdir

        if client_config is None:
            client_config = load_client_config()
        manifest: Manifest = load_validated_manifest(workdir, extra_vars)
        manifest_dict: Dict = load_merged_manifest_dict(get_manifest_path(workdir), extra_vars or {})
        logger.debug(f'Manifest loaded: {manifest}')

        lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
        user_auth = get_user_auth(client_config, lifecycle_url)

        logger.info(f'deploying workspace "{workdir}" (job {manifest.name} v{manifest.version}) to {lifecycle_url}')

        build_context = get_build_context(lifecycle_url, workdir, manifest, build_context_method)
        git_credentials = get_git_credentials(manifest, client_config)
        secret_vars = read_secret_vars(workdir, manifest)

        # see `lifecycle.endpoints.deploy::setup_deploy_endpoints::DeployEndpoint` for server-side implementation
        r = Requests.post(
            f'{lifecycle_url}/api/v1/deploy',
            json=get_deploy_request_payload(manifest_dict, git_credentials, secret_vars, build_context, force, build_flags),
            headers=get_auth_request_headers(user_auth),
        )
        response = parse_response_object(r, 'Lifecycle deploying error')
        deploy_id = response["id"]
        logger.info(f'job deployment requested: {deploy_id}')

        try:
            job_url = _wait_for_deployment_result(lifecycle_url, deploy_id, user_auth, [], [])
        except Exception as e:
            raise DeploymentError(e)
        logger.info(f'Job "{manifest.name}" has been deployed. Check out {job_url} to access your Job')
    finally:
        if tmp_file is not None and os.path.exists(tmp_file) and os.path.isfile(tmp_file):
            os.remove(tmp_file)


def get_deploy_request_payload(
    manifest_dict: Dict,
    git_credentials: Optional[Credentials],
    secret_vars: SecretVars,
    build_context: Optional[str],
    force: bool,
    build_flags: List[str],
) -> Dict:
    return {
        "manifest": manifest_dict,
        "git_credentials": git_credentials.model_dump() if git_credentials is not None else None,
        "secret_vars": secret_vars.model_dump(),
        "build_context": build_context,
        "force": force,
        "build_flags": build_flags,
    }


@backoff.on_exception(
    backoff.fibo, TimeoutError, max_value=3, max_time=DEPLOYMENT_TIMEOUT_SECS, jitter=None, logger=None
)
def _wait_for_deployment_result(lifecycle_url: str, deploy_id: str, user_auth: str, phases: List[Optional[str]], warningss: List[Optional[str]]) -> str:
    # see `lifecycle.endpoints.deploy::setup_deploy_endpoints::DeployIdEndpoint` for server-side implementation
    r = Requests.get(
        f'{lifecycle_url}/api/v1/deploy/{deploy_id}',
        headers=get_auth_request_headers(user_auth),
    )
    response = parse_response_object(r, 'Lifecycle deployment status')
    warnings = response.get('warnings')
    if not warningss or warningss[-1] != warnings:  # don't print the same warnings again
        warningss.append(warnings)
        if warnings:
            logger.warning(warnings)

    status = response['status'].lower()
    if status == 'failed':
        raise RuntimeError(response['error'])
    if status == 'done':
        return response.get('job', {}).get('pub_url', '')

    phase = response.get('phase')
    if not phases or phases[-1] != phase:  # don't print the same phase again
        phases.append(phase)
        if phase:
            logger.info(f'deployment in progress: {phase}...')
        else:
            logger.info(f'deployment in progress...')

    raise TimeoutError('Deployment timeout error')


def get_git_credentials(manifest: Manifest, client_config: ClientConfig) -> Optional[Credentials]:
    if manifest.git.remote in client_config.git_credentials:
        return client_config.git_credentials[manifest.git.remote]

    split = urlsplit(manifest.git.remote)

    url = f'{split.scheme}://{split.netloc}{split.path}'
    if url in client_config.git_credentials:
        return client_config.git_credentials[url]

    url = f'{split.scheme}://{split.netloc}'
    if url in client_config.git_credentials:
        return client_config.git_credentials[url]

    url = f'{split.netloc}'
    if url in client_config.git_credentials:
        return client_config.git_credentials[url]

    return None


def get_build_context(lifecycle_url: str, workdir: str, manifest: Manifest, build_context_method: BuildContextMethod) -> Optional[str]:
    """
    Use compressed local build context in order to prevent the need to commit every change.
    """
    if build_context_method == BuildContextMethod.default:
        build_context_method = _determine_default_build_context_method(lifecycle_url, manifest)
    if build_context_method == BuildContextMethod.local:
        return encode_build_context(workdir)
    else:
        return None


def _determine_default_build_context_method(lifecycle_url: str, manifest: Manifest) -> BuildContextMethod:
    """
    Decide whether to use local build context or to fetch source from git.
    It avoids fetching from remote git when using samples from local project repository.
    """
    if _is_url_localhost(lifecycle_url) and manifest.owner_email == 'sample@example.com':
        logger.info('using local build context due to deploying to localhost')
        return BuildContextMethod.local
    return BuildContextMethod.git


def _is_url_localhost(url: str) -> bool:
    split = urlsplit(url)
    return split.hostname in {'localhost', '127.0.0.1', '::1'}


def encode_build_context(workdir: str) -> str:
    """Compress build context directory to .tar.gz and encode it to base64 string"""
    tar_fileobj = io.BytesIO()
    workdir_path = Path(workdir)
    if workdir_path.is_file():
        workdir_path = workdir_path.parent

    ignore_file = workdir_path / '.gitignore'
    if ignore_file.is_file():
        logger.debug(f'skipping file patterns found in {ignore_file}')
        inclusion_matcher = FilenameMatcher(ignore_file.read_text().splitlines())
    else:
        inclusion_matcher = FilenameMatcher()

    files_count = 0
    with tarfile.open(fileobj=tar_fileobj, mode='w:gz') as tar:
        for relative_path in inclusion_matcher.list_files(workdir_path):
            absolute: Path = workdir_path / relative_path
            tar.add(str(absolute), arcname=str(relative_path))
            files_count += 1
    encoded = b64encode(tar_fileobj.getvalue()).decode()
    logger.info(f"local build context encoded: {files_count} files, {format_bytes(len(encoded))}")
    return encoded
