#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
from typing import Dict
import secrets
import string

import yaml
from jinja2 import Template, StrictUndefined

from racetrack_client.utils.shell import shell_output
from racetrack_client.log.logs import init_logs, configure_logs, get_logger

logger = get_logger(__name__)


def main():
    init_logs()
    configure_logs(log_level='debug')

    templates_path = Path('kustomize/external')
    assert templates_path.is_dir(), f"can't find directory: {templates_path}. Make sure you're in the root of repository"
    generated_path = Path('kustomize/generated')
    if generated_path.exists():
        logger.info('cleaning up "generated" directory')
        shutil.rmtree(generated_path)
    generated_path.mkdir()

    script_path = Path(os.path.realpath(__file__))
    config_yaml = script_path.with_name('config.yaml').read_text()
    context_vars: Dict = yaml.load(config_yaml, Loader=yaml.FullLoader)

    if not context_vars.get('POSTGRES_PASSWORD'):
        context_vars['POSTGRES_PASSWORD'] = (password := generate_password())
        logger.info(f'POSTGRES_PASSWORD generated: {password}')

    if not context_vars.get('SECRET_KEY'):
        context_vars['SECRET_KEY'] = (password := generate_password())
        logger.info(f'SECRET_KEY generated: {password}')

    if not context_vars.get('AUTH_KEY'):
        context_vars['AUTH_KEY'] = (password := generate_password())
        logger.info(f'AUTH_KEY generated: {password}')

    os.environ['AUTH_KEY'] = context_vars['AUTH_KEY']
    token = shell_output('python -m lifecycle generate-auth pub --short').strip()
    logger.info(f"PUB's token generated: {token}")
    context_vars['PUB_TOKEN'] = token
    token = shell_output('python -m lifecycle generate-auth dashboard --short').strip()
    logger.info(f"Dashboard's token generated: {token}")
    context_vars['DASHBOARD_TOKEN'] = token
    token = shell_output('python -m lifecycle generate-auth image-builder --short').strip()
    logger.info(f"Image-builder's token generated: {token}")
    context_vars['IMAGE_BUILDER_TOKEN'] = token

    assert context_vars['your_ip'], "your_ip configuration has to be filled"

    template_dir(templates_path, generated_path, context_vars)
    logger.info(f'resources are generated in "{generated_path}", ready to be deployed.')


def template_dir(src_directory: Path, dst_directory: Path, context_vars: Dict):
    dst_directory.mkdir(parents=True, exist_ok=True)
    for src_child in src_directory.iterdir():
        dst_child = dst_directory / src_child.relative_to(src_directory)
        if src_child.is_dir():
            template_dir(src_child, dst_child, context_vars)
        else:
            template_file(src_child, dst_child, context_vars)


def template_file(src_file: Path, dst_file: Path, context_vars: Dict):
    template_content: str = src_file.read_text()
    template = Template(template_content, undefined=StrictUndefined)
    templated: str = template.render(**context_vars)
    dst_file.write_text(templated)
    logger.debug(f'file templated: {dst_file}')


def generate_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))


if __name__ == '__main__':
    main()
