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
    assert templates_path.is_dir(), f"can't find directory: {templates_path}. Make sure you're in the root of the repository"
    generated_path = Path('kustomize/generated')
    if generated_path.exists():
        logger.info('cleaning up directory "kustomize/generated"')
        shutil.rmtree(generated_path)
    generated_path.mkdir()

    script_path = Path(os.path.realpath(__file__))
    config_yaml = script_path.with_name('config.yaml').read_text()
    context_vars: Dict = yaml.load(config_yaml, Loader=yaml.FullLoader)

    ensure_has_config_var(context_vars, 'registry_hostname', 'Enter Docker Registry hostname')
    ensure_has_config_var(context_vars, 'registry_username', 'Enter Docker Registry username')
    ensure_has_config_var(context_vars, 'read_registry_token', 'Enter token for reading Docker Registry')
    ensure_has_config_var(context_vars, 'write_registry_token', 'Enter token for writing Docker Registry')
    ensure_has_config_var(context_vars, 'your_ip', 'Enter your IP address for all public services exposed by Ingress, e.g. 1.1.1.1')

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
    logger.debug(f"PUB's token generated: {token}")
    context_vars['PUB_TOKEN'] = token
    token = shell_output('python -m lifecycle generate-auth image-builder --short').strip()
    logger.debug(f"Image-builder's token generated: {token}")
    context_vars['IMAGE_BUILDER_TOKEN'] = token

    registry_hostname = context_vars['registry_hostname']
    registry_username = context_vars['registry_username']
    read_registry_token = context_vars['read_registry_token']
    write_registry_token = context_vars['write_registry_token']
    registry_secrets_content = shell_output(f'''kubectl create secret docker-registry docker-registry-read-secret \\
    --docker-server="{registry_hostname}" \\
    --docker-username="{registry_username}" \\
    --docker-password="{read_registry_token}" \\
    --namespace=racetrack \\
    --dry-run=client -oyaml''').strip()
    registry_secrets_content += '\n---\n'
    registry_secrets_content += shell_output(f'''kubectl create secret docker-registry docker-registry-write-secret \\
    --docker-server="{registry_hostname}" \\
    --docker-username="{registry_username}" \\
    --docker-password="{write_registry_token}" \\
    --namespace=racetrack \\
    --dry-run=client -oyaml''').strip()
    registry_secrets_file = generated_path / 'docker-registry-secret.yaml'
    registry_secrets_file.write_text(registry_secrets_content)
    logger.debug(f"encoded Docker registry secrets: {registry_secrets_file}")

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
    assert length >= 16, 'password should be at least 16 characters long'
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))


def ensure_has_config_var(context_vars: Dict, config_name: str, missing_prompt: str):
    config_value = context_vars.get(config_name)
    while not config_value:
        config_value = input(missing_prompt + ': ').strip()
    context_vars[config_name] = config_value


if __name__ == '__main__':
    main()
