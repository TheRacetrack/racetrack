#!/usr/bin/env python3
import io
import subprocess
from dataclasses import dataclass, asdict
import json
import logging
import os
from pathlib import Path
import secrets
import string
import sys
from typing import Dict, Optional
import urllib.request

from racetrack_client.log.logs import configure_logs
from racetrack_client.utils.shell import shell_output, CommandError
from racetrack_client.utils.request import Requests, ResponseError

logger = logging.getLogger('racetrack')

LOG_FORMAT = '\033[2m[%(asctime)s]\033[0m %(levelname)s %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOCAL_CONFIG_FILE = (Path() / 'setup.json').absolute()
NON_INTERACTIVE: bool = os.environ.get('RT_NON_INTERACTIVE', '0') == '1'
GIT_BRANCH = '308-provide-instructions-on-how-to-install-racetrack-to-a-vm-instance'
GIT_REPOSITORY_PREFIX = f'https://raw.githubusercontent.com/TheRacetrack/racetrack/{GIT_BRANCH}/'
GRAFANA_DASHBOARDS = ['image-builder', 'jobs', 'lifecycle', 'postgres', 'pub']


def main():
    configure_logs(log_level='debug')
    logger.info('Welcome to the standalone Racetrack installer')

    if sys.version_info[:2] < (3, 8):
        logger.warning(f'This installer requires Python 3.8 or higher, but found: {sys.version_info}')

    config: SetupConfig = load_local_config()

    if not config.install_dir:
        config.install_dir = prompt_text('Choose installation directory', Path().absolute().as_posix())
        save_local_config(config)
    else:
        logger.debug(f'Installation directory set to: {config.install_dir}')

    logger.info('Installing Racetrack to local Docker Engine')
    install_to_docker(config)


def install_to_docker(config: 'SetupConfig'):
    install_dir = Path(config.install_dir).expanduser().absolute()
    if not install_dir.is_dir():
        install_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f'Created installation directory at {install_dir.absolute()}')
    os.chdir(install_dir.as_posix())

    if not config.external_address:
        config.external_address = prompt_text(
            'Enter the external address that your Racetrack will be accessed at (IP or domain name)', 'http://127.0.0.1')
        save_local_config(config)
    else:
        logger.debug(f'External remote address set to: {config.external_address}')

    _verify_docker()
    if not config.docker_gid:
        config.docker_gid = shell_output("(getent group docker || echo 'docker:x:0') | cut -d: -f3").strip()
        logger.debug(f'Docker group ID set to: {config.docker_gid}')

    _generate_secrets(config)

    if not (plugins_path := Path('.plugins')).is_dir():
        logger.info('Creating plugins volume…')
        plugins_path.mkdir(parents=True, exist_ok=True)
        plugins_path.chmod(0o777)
        metrics_path = plugins_path / 'metrics'
        metrics_path.mkdir(parents=True, exist_ok=True)
        metrics_path.chmod(0o777)

    logger.info('Templating config files…')
    template_repository_file('utils/standalone-wizard/templates/docker-compose.template.yaml', 'docker-compose.yaml', {
        'DOCKER_GID': config.docker_gid,
        'PUB_AUTH_TOKEN': config.pub_auth_token,
        'IMAGE_BUILDER_AUTH_TOKEN': config.image_builder_auth_token,
        'POSTGRES_PASSWORD': config.postgres_password,
        'EXTERNAL_ADDRESS': config.external_address,
    })
    template_repository_file('utils/standalone-wizard/templates/.env.template', '.env', {
        'POSTGRES_PASSWORD': config.postgres_password,
        'AUTH_KEY': config.auth_key,
        'SECRET_KEY': config.django_secret_key,
    })
    template_repository_file('utils/standalone-wizard/templates/lifecycle.template.yaml', 'config/lifecycle.yaml', {
        'EXTERNAL_ADDRESS': config.external_address,
    })
    download_repository_file('utils/standalone-wizard/templates/Makefile', 'Makefile')
    download_repository_file('image_builder/tests/sample/compose.yaml', 'config/image_builder.yaml')
    download_repository_file('utils/wait-for-lifecycle.sh', 'utils/wait-for-lifecycle.sh')
    download_repository_file('postgres/init.sql', 'config/postgres/init.sql')
    download_repository_file('utils/prometheus/prometheus.yaml', 'utils/prometheus/prometheus.yaml')
    download_repository_file('utils/grafana/datasource.yaml', 'utils/grafana/datasource.yaml')
    download_repository_file('utils/grafana/dashboards-all.yaml', 'utils/grafana/dashboards-all.yaml')
    for dashboard in GRAFANA_DASHBOARDS:
        download_repository_file(f'utils/grafana/dashboards/{dashboard}.json', f'utils/grafana/dashboards/{dashboard}.json')
    download_repository_file('sample/python-class/adder.py', 'sample/python-class/adder.py')
    download_repository_file('sample/python-class/job.yaml', 'sample/python-class/job.yaml')

    logger.info('Starting up containers…')
    shell('DOCKER_BUILDKIT=1 DOCKER_SCAN_SUGGEST=false docker compose up -d --no-build --pull=always', raw_output=True)

    logger.info('Waiting until Racetrack is operational…')
    shell('LIFECYCLE_URL=http://127.0.0.1:7102 bash utils/wait-for-lifecycle.sh')

    try:
        auth_token = get_admin_auth_token('admin')
        logger.info('Changing default admin password…')
        change_admin_password(auth_token, 'admin', config.admin_password)
    except ResponseError as e:
        if not e.status_code == 401:  # Unauthorized
            raise e

    config.admin_auth_token = get_admin_auth_token(config.admin_password)

    logger.info('Configuring racetrack client…')
    racetrack_cmd = 'python -m racetrack_client '
    shell(racetrack_cmd + 'set remote http://127.0.0.1:7102')
    shell(racetrack_cmd + f'login {config.admin_auth_token}')
    logger.info('Installing plugins…')
    shell(racetrack_cmd + 'plugin install github.com/TheRacetrack/plugin-python-job-type')
    shell(racetrack_cmd + 'plugin install github.com/TheRacetrack/plugin-docker-infrastructure')

    logger.info(f'''Racetrack is ready to use.
Visit Racetrack Dashboard at {config.external_address}:7103/dashboard
Log in with username: admin, password: {config.admin_password}
To deploy here, configure your racetrack client: racetrack set remote {config.external_address}:7102/lifecycle
''')


def _verify_docker():
    logger.info('Verifying Docker installation…')
    try:
        shell('docker --version', print_stdout=False)
    except CommandError as e:
        logger.warning('Docker is unavailable. Please install Docker Engine: https://docs.docker.com/engine/install/ubuntu/')
        if not prompt_shell_command('Would you like to install Docker by executing the following command?', '''
curl -fsSL https://get.docker.com -o install-docker.sh
sh install-docker.sh
'''):
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


def _generate_secrets(config: 'SetupConfig'):
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


def get_admin_auth_token(password: str) -> str:
    response = Requests.post('http://127.0.0.1:7103/dashboard/api/v1/users/login', json={
        'username': 'admin',
        'password': password,
    })
    response.raise_for_status()
    return response.json()['token']


def change_admin_password(auth_token: str, old_pass: str, new_pass: str):
    response = Requests.put('http://127.0.0.1:7103/dashboard/api/v1/users/change_password', headers={
        'X-Racetrack-Auth': auth_token,
    }, json={
        'old_password': old_pass,
        'new_password': new_pass,
    })
    response.raise_for_status()
    logger.info('admin password changed')


@dataclass
class SetupConfig:
    infrastructure: str = ''
    install_dir: str = ''
    postgres_password: str = ''
    django_secret_key: str = ''
    auth_key: str = ''
    docker_gid: str = ''
    pub_auth_token: str = ''
    image_builder_auth_token: str = ''
    external_address: str = ''
    admin_password: str = ''
    admin_auth_token: str = ''


def load_local_config() -> SetupConfig:
    local_file = Path(LOCAL_CONFIG_FILE)
    if local_file.is_file():
        logger.info(f'Using local setup config found at {local_file.absolute()}')
        config_dict = json.loads(local_file.read_text())
        return SetupConfig(**config_dict)
    else:
        config = SetupConfig()
        save_local_config(config)
        logger.info(f'Setup configuration created at {local_file.absolute()}')
        return config


def save_local_config(config: SetupConfig):
    config_json: str = json.dumps(asdict(config), indent=4)
    local_file = Path(LOCAL_CONFIG_FILE)
    local_file.write_text(config_json)


def prompt_text(question: str, default: str) -> str:
    if '\n' in question:
        print(f'{question}\n[default: {default}]: ', end='')
    else:
        print(f'{question} [default: {default}]: ', end='')
    if NON_INTERACTIVE:
        return default
    value = input()
    if value == '':
        logger.debug(f'Default set: {default}')
        return default
    return value


def prompt_bool(question: str, default: bool = True) -> bool:
    while True:
        if default is True:
            options = '[Y/n]'
        else:
            options = '[y/N]'
        if '\n' in question:
            print(f'{question}\n{options}: ', end='')
        else:
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


def prompt_shell_command(question: str, snippet: str) -> bool:
    snippet = snippet.strip()
    if not prompt_bool(f'{question}\n{snippet}'):
        return False
    for command in snippet.splitlines():
        shell(command)
    return True


def generate_password(length: int = 32) -> str:
    assert length >= 16, 'password should be at least 16 characters long'
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def template_file(src_file: Path, dst_file: Path, context_vars: Dict[str, str]):
    template = string.Template(src_file.read_text())
    outcome: str = template.substitute(**context_vars)
    dst_file.write_text(outcome)


def template_repository_file(src_relative_url: str, dst_path: str, context_vars: Dict[str, str]):
    src_file_url = GIT_REPOSITORY_PREFIX + src_relative_url
    logger.debug(f'Downloading {src_file_url}')
    with urllib.request.urlopen(src_file_url) as response:
        src_content: bytes = response.read()
    template = string.Template(src_content.decode())
    outcome: str = template.substitute(**context_vars)
    dst_file = Path(dst_path)
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    dst_file.write_text(outcome)


def download_repository_file(src_relative_url: str, dst_path: str):
    src_file_url = GIT_REPOSITORY_PREFIX + src_relative_url
    logger.debug(f'Downloading {src_file_url}')
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


def shell(
    cmd: str,
    workdir: Optional[Path] = None,
    print_stdout: bool = True,
    raw_output: bool = False,
) -> io.StringIO:
    logger.debug(f'Command: {cmd}')
    if len(cmd) > 4096:  # see https://github.com/torvalds/linux/blob/v5.11/drivers/tty/n_tty.c#L1681
        raise RuntimeError('maximum tty line length has been exceeded')

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


if __name__ == '__main__':
    main()
