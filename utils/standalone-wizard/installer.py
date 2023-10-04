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
from typing import Optional

logger = logging.getLogger('racetrack')

LOG_FORMAT = '\033[2m[%(asctime)s]\033[0m %(levelname)s %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

LOCAL_CONFIG_FILE = 'setup.json'

NON_INTERACTIVE: bool = os.environ.get('RT_NON_INTERACTIVE', '1') == '1'


def main():
    init_logs()
    logger.info('Welcome to Racetrack installer')

    if sys.version_info[:2] < (3, 8):
        logger.warning(f'This installer requires Python 3.8 or higher. Found: {sys.version_info}')

    config: InstallationConfig = load_local_config()

    if config.install_dir:
        logger.debug(f'Installation directory configured: {config.install_dir}')
    else:
        config.install_dir = prompt_text('Choose installation directory', '~/racetrack')
        save_local_config(config)

    if config.infrastructure:
        logger.debug(f'infrastructure target configured: {config.infrastructure}')
    else:
        config.infrastructure = prompt_text('Choose infrastructure target to install Racetrack', 'docker',
                                            'docker - Docker Engine on this local machine')
        save_local_config(config)

    if config.infrastructure == 'docker':
        install_to_docker(config)


@dataclass
class InstallationConfig:
    infrastructure: str = ''
    install_dir: str = ''


def install_to_docker(config: InstallationConfig):
    install_path = Path(config.install_dir).expanduser()
    if not install_path.is_dir():
        install_path.mkdir(parents=True, exist_ok=True)

    prompt_bool('Docker not available. Would you like to install Docker Engine?')

    # generate secrets, keep in local reusable files
    # install docker, non-root, docker compose


def load_local_config() -> InstallationConfig:
    local_file = Path(LOCAL_CONFIG_FILE)
    if local_file.is_file():
        logger.info(f'Found local setup config at {local_file.absolute()}')
        config_dict = json.loads(local_file.read_text())
        return InstallationConfig(**config_dict)
    else:
        logger.info(f'Creating setup configuration at {local_file.absolute()}')
        config = InstallationConfig()
        save_local_config(config)
        return config


def save_local_config(config: InstallationConfig):
    config_json: str = json.dumps(asdict(config), indent=4)
    local_file = Path(LOCAL_CONFIG_FILE)
    local_file.write_text(config_json)


def prompt_text(name: str, default: str, description: str = '') -> str:
    if NON_INTERACTIVE:
        return default
    if description:
        logger.info(f'{name} [default: {default}]:\n{description}')
    else:
        logger.info(f'{name} [default: {default}]: ')
    value = input()
    if value == '':
        logger.debug(f'Chosen default: {default}')
        return default
    return value


def prompt_bool(name: str, default: bool = True) -> bool:
    if NON_INTERACTIVE:
        return default
    while True:
        if default is True:
            logger.info(f'{name} [Y/n]: ')
        else:
            logger.info(f'{name} [y/N]: ')
        value = input()
        if value == '':
            return default
        if value.lower() == 'y':
            return True
        if value.lower() == 'n':
            return False


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
    """
    Run system shell command.
    Print live stdout as it comes (line by line) and capture entire output in case of errors.
    :param cmd: shell command to run
    :param workdir: working directory for the command
    :param print_stdout: whether to print stdout from a subprocess to the main process stdout
    :param read_bytes: whether to read raw bytes from the subprocess stdout instead of whole lines
    :param output_filename: file to write the output in real time
    :raises:
        CommandError: in case of non-zero command exit code.
    """
    _run_shell_command(cmd, workdir, print_stdout, output_filename, read_bytes)


def shell_output(
    cmd: str,
    workdir: Optional[Path] = None,
    print_stdout: bool = False,
    read_bytes: bool = False,
    output_filename: Optional[str] = None,
) -> str:
    """
    Run system shell command and return its output.
    Print live stdout as it comes (line by line) and capture entire output in case of errors.
    :param cmd: shell command to run
    :param workdir: working directory for the command
    :param print_stdout: whether to print stdout from a subprocess to the main process stdout
    :param read_bytes: whether to read raw bytes from the subprocess stdout instead of whole lines
    :param output_filename: file to write the output in real time
    """
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


if __name__ == '__main__':
    main()
