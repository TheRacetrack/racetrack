import io
import json
import logging
import os
import secrets
import shutil
import string
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Union

from pydantic import BaseModel

from racetrack_client.utils.request import Requests, ResponseError, RequestError
from racetrack_client.utils.shell import shell_output, CommandError

logger = logging.getLogger('racetrack')

LOCAL_CONFIG_FILE = (Path() / os.environ.get('CONFIG_FILE', 'setup.json')).absolute()
NON_INTERACTIVE: bool = os.environ.get('RT_NON_INTERACTIVE', '0') == '1'
RT_BRANCH = os.environ.get('RT_BRANCH', 'master')
GIT_REPOSITORY_PREFIX = f'https://raw.githubusercontent.com/TheRacetrack/racetrack/{RT_BRANCH}/'


def verify_docker():
    logger.info('Verifying Docker installation…')
    try:
        shell('docker --version', print_stdout=False)
    except CommandError as e:
        logger.error('Docker is unavailable. Please install Docker Engine: https://docs.docker.com/engine/install/ubuntu/')
        raise e

    try:
        shell('docker ps', print_stdout=False)
    except CommandError as e:
        logger.error('Docker is not managed by this user. Please manage Docker as a non-root user: https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user')
        raise e

    try:
        shell('docker compose version', print_stdout=False)
    except CommandError as e:
        logger.error('Please install Docker Compose plugin: https://docs.docker.com/compose/install/linux/')
        raise e


def configure_docker_gid(config: 'SetupConfig'):
    if not config.docker_gid:
        config.docker_gid = shell_output("(getent group docker || echo 'docker:x:0') | cut -d: -f3").strip()
        logger.debug(f'Docker group ID is {config.docker_gid}')


def generate_secrets(config: 'SetupConfig'):
    if not config.postgres_password:
        config.postgres_password = generate_password()
        logger.info(f'Generated PostgreSQL password: {config.postgres_password}')
    if not config.django_secret_key:
        config.django_secret_key = generate_password()
        logger.info(f'Generated Django secret key: {config.django_secret_key}')
    if not config.auth_key:
        config.auth_key = generate_password()
        logger.info(f'Generated Auth key: {config.auth_key}')
    if not config.admin_password:
        config.admin_password = generate_password()
        logger.info(f'Generated Admin password: {config.admin_password}')

    if not config.pub_auth_token:
        logger.info("Pulling Lifecycle image…")
        shell('docker pull ghcr.io/theracetrack/racetrack/lifecycle:latest', raw_output=True)
        logger.info("Generating Pub's auth token…")
        config.pub_auth_token = generate_auth_token(config.auth_key, 'pub')
    if not config.image_builder_auth_token:
        logger.info("Generating Image builder's auth token…")
        config.image_builder_auth_token = generate_auth_token(config.auth_key, 'image-builder')
    save_local_config(config)


def login_first_time(config: 'SetupConfig', lifecycle_url: str):
    # Try to log in with admin:admin. If it succeeds, change the password to something more secure.
    try:
        auth_token = get_admin_auth_token('admin', lifecycle_url)
        logger.info('Changing default admin password…')
        change_admin_password(auth_token, 'admin', config.admin_password, lifecycle_url)
    except ResponseError as e:
        # In case of 401 Unauthorized, password is already changed
        if e.status_code != 401:
            raise e
    config.admin_auth_token = get_admin_auth_token(config.admin_password, lifecycle_url)

    logger.info('Configuring racetrack client…')
    racetrack_cmd = 'python -m racetrack_client '
    shell(racetrack_cmd + f'set remote {lifecycle_url}')
    shell(racetrack_cmd + f'login {config.admin_auth_token}')


def get_admin_auth_token(password: str, lifecycle_url: str) -> str:
    response = Requests.post(f'{lifecycle_url}/api/v1/users/login', json={
        'username': 'admin',
        'password': password,
    })
    response.raise_for_status()
    return response.json()['token']


def change_admin_password(auth_token: str, old_pass: str, new_pass: str, lifecycle_url: str):
    response = Requests.put(f'{lifecycle_url}/api/v1/users/change_password', headers={
        'X-Racetrack-Auth': auth_token,
    }, json={
        'old_password': old_pass,
        'new_password': new_pass,
    })
    response.raise_for_status()
    logger.info('admin password changed')


class RemoteGatewayConfig(BaseModel):
    remote_gateway_token: str = ''
    pub_remote_image: str = ''


class SetupConfig(BaseModel):
    infrastructure: str = ''
    postgres_password: str = ''
    django_secret_key: str = ''
    auth_key: str = ''
    docker_gid: str = ''
    pub_auth_token: str = ''
    image_builder_auth_token: str = ''
    external_address: str = ''
    admin_password: str = ''  # not the actual password but the one that is supposed to be set
    admin_auth_token: str = ''
    registry_hostname: str = ''
    registry_username: str = ''
    read_registry_token: str = ''
    write_registry_token: str = ''
    registry_namespace: str = ''
    public_ip: str = ''
    kubernetes_namespace: str = ''
    remote_gateway_config: RemoteGatewayConfig = RemoteGatewayConfig()


def load_local_config() -> SetupConfig:
    local_file = Path(LOCAL_CONFIG_FILE)
    if local_file.is_file():
        logger.info(f'Using local setup config found at {local_file.absolute()}')
        config_dict = json.loads(local_file.read_text())
        return SetupConfig.parse_obj(config_dict)
    else:
        config = SetupConfig()
        save_local_config(config)
        logger.info(f'Setup configuration created at {local_file.absolute()}')
        return config


def save_local_config(config: SetupConfig):
    config_json: str = json.dumps(config.dict(), indent=4)
    local_file = Path(LOCAL_CONFIG_FILE)
    local_file.write_text(config_json)


def prompt_text(question: str, default: str, env_var: str) -> str:
    while True:
        if not default:
            default_info = ''
        elif '\n' in question:
            default_info = f'\n[default: {default}]'
        else:
            default_info = f' [default: {default}]'
        print(f'{question}{default_info}: ', end='')
        env_value = os.environ.get(env_var)
        if env_value:
            logger.debug(f'Value set from env variable {env_var}: {env_value}')
            return env_value
        if NON_INTERACTIVE:
            return default
        value = input()
        if value == '' and default:
            return default
        if value:
            return value


def prompt_bool(question: str, default: bool = True) -> bool:
    while True:
        if default is True:
            options = '[Y/n]'
        else:
            options = '[y/N]'
        print(f'{question} {options}: ', end='')
        if NON_INTERACTIVE:
            return default
        value = input()
        if value == '':
            return default
        if value.lower() == 'y':
            return True
        if value.lower() == 'n':
            return False


def prompt_text_choice(question: str, answers: Dict[str, str], default: str, env_var: str) -> str:
    prompt = question.strip()
    answer_key_by_index: Dict[str, str] = {}
    for index, answer_key in enumerate(answers.keys()):
        answer_prompt = answers[answer_key]
        answer_key_by_index[str(index + 1)] = answer_key
        prompt += f'\n  {index+1}. {answer_key} - {answer_prompt}'
    env_value = os.environ.get(env_var)
    if env_value:
        logger.debug(f'Value set from env variable {env_var}: {env_value}')
        return env_value
    if NON_INTERACTIVE:
        return default
    while True:
        print(f'{prompt}\n[1-{len(answers)}] [default: {default}]: ', end='')
        value = input()
        if value == '' and default:
            return default
        if value in answers.keys():
            return value
        if value in answer_key_by_index.keys():
            return answer_key_by_index.get(value)


def ensure_var_configured(
    current_value: str,
    short_field_name: str,
    default: str,
    prompt_name: str,
) -> str:
    if not current_value:
        env_var = f'RT_{short_field_name}'.upper()
        return prompt_text(prompt_name, default, env_var)
    else:
        logger.debug(f'{short_field_name} set to {current_value}')
        return current_value


def generate_password(length: int = 32) -> str:
    assert length >= 16, 'password should be at least 16 characters long'
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def template_repository_file(src_relative_url: str, dst_path: str, context_vars: Dict[str, str]):
    src_file_url = GIT_REPOSITORY_PREFIX + src_relative_url
    logger.debug(f'Templating {dst_path}')
    with urllib.request.urlopen(src_file_url) as response:
        src_content: bytes = response.read()
    template = string.Template(src_content.decode())
    outcome: str = template.substitute(**context_vars)
    dst_file = Path(dst_path)
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    dst_file.write_text(outcome)


def download_repository_file(src_relative_url: str, dst_path: Union[str, Path]):
    src_file_url = GIT_REPOSITORY_PREFIX + src_relative_url
    logger.debug(f'Creating {dst_path}')
    with urllib.request.urlopen(src_file_url) as response:
        src_content: bytes = response.read()
    dst_file = Path(dst_path)
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    dst_file.write_bytes(src_content)


def generate_auth_token(auth_key: str, service_name: str) -> str:
    return shell_output(
        f'docker run --rm --name lifecycle-tmp'
        f' --env AUTH_KEY="{auth_key}"'
        f' ghcr.io/theracetrack/racetrack/lifecycle:latest'
        f' python -u -m lifecycle generate-auth "{service_name}" --short'
        f' 2>/dev/null'
    ).strip()


def get_generated_dir() -> Path:
    generated_dir = Path('generated')
    if generated_dir.exists():
        if prompt_bool(f'Directory "{generated_dir}" already exists. Would you like to clear it?'):
            logger.info(f'cleaning up directory "{generated_dir}"')
            shutil.rmtree(generated_dir)
    generated_dir.mkdir(parents=True, exist_ok=True)
    return generated_dir


def wait_for_lifecycle(url: str, attempts: int = 120):
    while True:
        try:
            response = Requests.get(f'{url}/ready')
            if response.status_code == 200:
                return
        except RequestError:
            pass
        attempts -= 1
        if attempts < 1:
            raise RuntimeError('Lifecycle service is not ready')
        time.sleep(1)
        logger.debug('Waiting for Lifecycle to be ready…')


def shell(
    cmd: str,
    workdir: Optional[Path] = None,
    print_stdout: bool = True,
    raw_output: bool = False,
) -> io.StringIO:
    logger.debug(f'Executing command: {cmd}')
    if raw_output:
        process = subprocess.Popen(cmd, stdout=None, stderr=None, shell=True, cwd=workdir)
    else:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=workdir)
    try:
        captured_stream = io.StringIO()
        if raw_output:
            process.wait()
            if process.returncode != 0:
                raise CommandError(cmd, '', process.returncode)
            return captured_stream

        # fork command output to stdout, captured buffer and output file
        for line in iter(process.stdout.readline, b''):
            line_str = line.decode()

            if print_stdout:
                sys.stdout.write(line_str)
                sys.stdout.flush()
            captured_stream.write(line_str)

        process.wait()
        if process.returncode != 0:
            stdout = captured_stream.getvalue()
            raise CommandError(cmd, stdout, process.returncode)
        return captured_stream
    except KeyboardInterrupt:
        logger.warning('killing subprocess')
        process.kill()
        raise
