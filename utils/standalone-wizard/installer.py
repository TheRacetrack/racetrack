#!/usr/bin/env python3
from dataclasses import dataclass, asdict
import io
import json
import logging
import os
from pathlib import Path
import secrets
import string
import subprocess
import sys
from typing import Optional, Dict
import urllib.request

logger = logging.getLogger('racetrack')

LOG_FORMAT = '\033[2m[%(asctime)s]\033[0m %(levelname)s %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

LOCAL_CONFIG_FILE = (Path() / 'setup.json').absolute()

NON_INTERACTIVE: bool = os.environ.get('RT_NON_INTERACTIVE', '0') == '1'

# Requirements:
# python3, python3-pip
# python3 venv
# docker (non-root)
# docker compose
# wget
# git ?

# wget -O - https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/quickstart-up.sh | bash


def main():
    init_logs()
    logger.info('Welcome to standalone Racetrack installer')

    if sys.version_info[:2] < (3, 8):
        logger.warning(f'This installer requires Python 3.8 or higher. Found: {sys.version_info}')

    config: SetupConfig = load_local_config()

    if config.install_dir:
        logger.debug(f'Installation directory set to: {config.install_dir}')
    else:
        config.install_dir = prompt_text('Choose installation directory', '~/racetrack')
        save_local_config(config)

    if config.infrastructure:
        logger.debug(f'infrastructure target set to: {config.infrastructure}')
    else:
        config.infrastructure = prompt_text('Choose infrastructure target to install Racetrack', 'docker',
                                            'docker - Docker Engine on this local machine')
        save_local_config(config)

    if config.infrastructure == 'docker':
        install_to_docker(config)


@dataclass
class SetupConfig:
    infrastructure: str = ''
    install_dir: str = ''
    postgres_password: str = ''
    django_secret_key: str = ''
    auth_key: str = ''
    docker_gid: str = ''
    pub_auth_token: str = ''
    dashboard_auth_token: str = ''
    image_builder_auth_token: str = ''


def install_to_docker(config: SetupConfig):
    install_dir = Path(config.install_dir).expanduser().absolute()
    if not install_dir.is_dir():
        install_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f'Created installation directory: {install_dir.absolute()}')
    os.chdir(install_dir.as_posix())

    _verify_docker()
    if not config.docker_gid:
        config.docker_gid = shell_output("(getent group docker || echo 'docker:x:0') | cut -d: -f3").strip()

    _generate_secrets(config)

    if not Path('venv').is_dir():
        logger.info('Creating virtual environment…')
        shell('python3 -m venv venv')

    if not (plugins_path := Path('.plugins')).is_dir():
        logger.info('Creating plugins volume…')
        plugins_path.mkdir(parents=True, exist_ok=True)
        plugins_path.chmod(0o777)

    logger.info('Templating config files…')
    context_vars = asdict(config)
    template_repository_file('docker-compose.yaml', 'docker-compose.yaml', context_vars)

    # configure optional external address: IP / FQDN, http://127.0.0.1
    # setup registry
    # run docker compose: start containers
    # wait for lifecycle
    # install racetrack client
    # set current remote
    # change super-admin password
    # print admin auth token
    # log in as admin to racetrack client
    # install plugins: python3, docker
    # print dashboard address

    logger.info('Racetrack is ready to use')


def _verify_docker():
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


def _generate_secrets(config: SetupConfig):
    if not config.postgres_password:
        config.postgres_password = generate_password()
        logger.info(f'Generated PostgreSQL password: {config.postgres_password}')
    if not config.django_secret_key:
        config.django_secret_key = generate_password()
        logger.info(f'Generated Django secret key: {config.django_secret_key}')
    if not config.auth_key:
        config.auth_key = generate_password()
        logger.info(f'Generated Auth key: {config.auth_key}')

    if not config.pub_auth_token:
        config.pub_auth_token = generate_auth_token(config.auth_key, 'pub')
        logger.info("Pub's token generated")
    if not config.dashboard_auth_token:
        config.dashboard_auth_token = generate_auth_token(config.auth_key, 'dashboard')
        logger.info("Dashboard's token generated")
    if not config.image_builder_auth_token:
        config.image_builder_auth_token = generate_auth_token(config.auth_key, 'image-builder')
        logger.info("Image builder's token generated")
    save_local_config(config)


def load_local_config() -> SetupConfig:
    local_file = Path(LOCAL_CONFIG_FILE)
    if local_file.is_file():
        logger.info(f'Found local setup config at {local_file.absolute()}')
        config_dict = json.loads(local_file.read_text())
        return SetupConfig(**config_dict)
    else:
        logger.info(f'Creating setup configuration at {local_file.absolute()}')
        config = SetupConfig()
        save_local_config(config)
        return config


def save_local_config(config: SetupConfig):
    config_json: str = json.dumps(asdict(config), indent=4)
    local_file = Path(LOCAL_CONFIG_FILE)
    local_file.write_text(config_json)


def prompt_text(name: str, default: str, description: str = '') -> str:
    description = '\n' + description if description else ''
    logger.info(f'{name} [default: {default}]: {description}')
    if NON_INTERACTIVE:
        return default
    value = input()
    if value == '':
        logger.debug(f'Chosen default: {default}')
        return default
    return value


def prompt_bool(name: str, default: bool = True, description: str = '') -> bool:
    description = '\n' + description if description else ''
    while True:
        if default is True:
            logger.info(f'{name} [Y/n]: {description}')
        else:
            logger.info(f'{name} [y/N]: {description}')
        if NON_INTERACTIVE:
            return default
        value = input()
        if value == '':
            return default
        if value.lower() == 'y':
            return True
        if value.lower() == 'n':
            return False


def prompt_shell_command(snippet: str):
    snippet = snippet.strip()
    if prompt_bool('Do you want to execute the following command?', description=snippet):
        for command in snippet.splitlines():
            shell(command)


def init_logs():
    logging.basicConfig(stream=sys.stdout, format=LOG_FORMAT, level=logging.INFO, datefmt=LOG_DATE_FORMAT, force=True)

    for handler in logging.getLogger().handlers:
        handler.setFormatter(ColoredFormatter(handler.formatter))

    rt_logger = logging.getLogger('racetrack')
    rt_logger.setLevel(logging.DEBUG)


class ColoredFormatter(logging.Formatter):
    def __init__(self, plain_formatter):
        logging.Formatter.__init__(self)
        self.plain_formatter = plain_formatter

    log_level_templates = {
        'CRITICAL': '\033[1;31mCRIT \033[0m',
        'ERROR': '\033[1;31mERROR\033[0m',
        'WARNING': '\033[0;33mWARN \033[0m',
        'INFO': '\033[0;34mINFO \033[0m',
        'DEBUG': '\033[0;32mDEBUG\033[0m',
    }

    def format(self, record: logging.LogRecord):
        if record.levelname in self.log_level_templates:
            record.levelname = self.log_level_templates[record.levelname].format(record.levelname)
        return self.plain_formatter.format(record)


def shell(
    cmd: str,
    workdir: Optional[Path] = None,
    print_stdout: bool = True,
    read_bytes: bool = False,
    output_filename: Optional[str] = None,
):
    _run_shell_command(cmd, workdir, print_stdout, output_filename, read_bytes)


def shell_output(
    cmd: str,
    workdir: Optional[Path] = None,
    print_stdout: bool = False,
    read_bytes: bool = False,
    output_filename: Optional[str] = None,
) -> str:
    captured_stream = _run_shell_command(cmd, workdir, print_stdout, output_filename, read_bytes)
    return captured_stream.getvalue()


def _run_shell_command(
    cmd: str,
    workdir: Optional[Path] = None,
    print_stdout: bool = True,
    output_filename: Optional[str] = None,
    read_bytes: bool = False,
) -> io.StringIO:
    logger.debug(f'Command: {cmd}')
    if len(cmd) > 4096:  # see https://github.com/torvalds/linux/blob/v5.11/drivers/tty/n_tty.c#L1681
        raise RuntimeError('maximum tty line length has been exceeded')
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=workdir)
    output_file = open(output_filename, 'a') if output_filename else None
    try:
        # fork command output to stdout, captured buffer and output file
        captured_stream = io.StringIO()

        if read_bytes:
            while True:
                chunk: bytes = process.stdout.read(1)
                if chunk == b'':
                    break
                chunk_str = chunk.decode()

                if print_stdout:
                    sys.stdout.write(chunk_str)
                    sys.stdout.flush()
                if output_file is not None:
                    output_file.write(chunk_str)
                captured_stream.write(chunk_str)

        else:
            for line in iter(process.stdout.readline, b''):
                line_str = line.decode()

                if print_stdout:
                    sys.stdout.write(line_str)
                    sys.stdout.flush()
                if output_file is not None:
                    output_file.write(line_str)
                captured_stream.write(line_str)

        process.wait()
        if output_file is not None:
            output_file.close()
        if process.returncode != 0:
            stdout = captured_stream.getvalue()
            raise CommandError(cmd, stdout, process.returncode)
        return captured_stream
    except KeyboardInterrupt:
        logger.warning('killing subprocess')
        process.kill()
        raise


class CommandError(RuntimeError):
    def __init__(self, cmd: str, stdout: str, returncode: int):
        super().__init__()
        self.cmd = cmd
        self.stdout = stdout
        self.returncode = returncode

    def __str__(self):
        return f'command failed: {self.cmd}: {self.stdout}'


def generate_password(length: int = 32) -> str:
    assert length >= 16, 'password should be at least 16 characters long'
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def template_file(src_file: Path, dst_file: Path, context_vars: Dict[str, str]):
    template = string.Template(src_file.read_text())
    outcome: str = template.substitute(**context_vars)
    dst_file.write_text(outcome)


def template_repository_file(src_relative_url: str, dst_path: str, context_vars: Dict[str, str]):
    src_file_url = 'https://raw.githubusercontent.com/TheRacetrack/racetrack/master/' + src_relative_url
    with urllib.request.urlopen(src_file_url) as response:
        src_content: bytes = response.read()
    template = string.Template(src_content.decode())
    outcome: str = template.substitute(**context_vars)
    dst_file = Path(dst_path)
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    dst_file.write_text(outcome)


def generate_auth_token(auth_key: str, service_name: str) -> str:
    return shell_output(f'''
    docker run --rm -it --name lifecycle-tmp \\
     --env AUTH_KEY="{auth_key}" \\
     ghcr.io/theracetrack/racetrack/lifecycle:latest \\
     python -u -m lifecycle generate-auth "{service_name}" --short
    '''.strip()).strip()


if __name__ == '__main__':
    main()
