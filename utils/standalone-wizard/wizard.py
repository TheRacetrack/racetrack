#!/usr/bin/env python3
import io
import shutil
import subprocess
import json
import logging
import os
import time
from pathlib import Path
import secrets
import string
import sys
from typing import Dict, Optional, Union
import urllib.request

from pydantic import BaseModel

from racetrack_client.log.logs import configure_logs
from racetrack_client.utils.shell import shell_output, CommandError
from racetrack_client.utils.request import Requests, ResponseError, RequestError

logger = logging.getLogger('racetrack')

LOCAL_CONFIG_FILE = (Path() / os.environ.get('CONFIG_FILE', 'setup.json')).absolute()
NON_INTERACTIVE: bool = os.environ.get('RT_NON_INTERACTIVE', '0') == '1'
RT_BRANCH = os.environ.get('RT_BRANCH', 'master')
GIT_REPOSITORY_PREFIX = f'https://raw.githubusercontent.com/TheRacetrack/racetrack/{RT_BRANCH}/'
GRAFANA_DASHBOARDS = ['image-builder', 'jobs', 'lifecycle', 'postgres', 'pub']


def main():
    configure_logs(log_level='debug')
    logger.info('Welcome to the standalone Racetrack installer')

    if sys.version_info[:2] < (3, 8):
        logger.warning(f'This installer requires Python 3.8 or higher, but found: {sys.version_info}')

    config: SetupConfig = load_local_config()

    if not config.infrastructure:
        config.infrastructure = prompt_text_choice('Choose the infrastructure target to deploy Racetrack:', {
            'docker': 'Deploy Racetrack and its jobs to in-place Docker Engine.',
            'kubernetes': 'Deploy Racetrack and its jobs to Kubernetes.',
            'remote-docker': 'Deploy Jobs gateway to Docker Daemon host. Connect it with already running Racetrack.',
            'remote-kubernetes': 'Deploy Jobs gateway to external Kubernetes cluster. Connect it with already running Racetrack.',
        }, 'docker', 'RT_INFRASTRUCTURE')
    else:
        logger.debug(f'infrastructure set to {config.infrastructure}')

    if config.infrastructure == 'docker':
        install_to_docker(config)
    elif config.infrastructure == 'kubernetes':
        install_to_kubernetes(config)
    elif config.infrastructure == 'remote-docker':
        install_to_remote_docker(config)
    elif config.infrastructure == 'remote-kubernetes':
        install_to_remote_kubernetes(config)
    else:
        raise RuntimeError(f'Unsupported infrastructure: {config.infrastructure}')


def install_to_docker(config: 'SetupConfig'):
    logger.info('Installing Racetrack to local Docker Engine')

    if not config.external_address:
        host_ips = shell_output('hostname --all-ip-addresses').strip().split(' ')
        logger.info(f'IP addresses for network interfaces on this host: {", ".join(host_ips)}')
        default_address = f'http://{host_ips[-1]}' if host_ips else 'http://127.0.0.1'
        config.external_address = prompt_text(
            'Enter the external address that your Racetrack will be accessed at (IP or domain name)',
            default_address, 'RT_EXTERNAL_ADDRESS'
        )
        save_local_config(config)
    else:
        logger.debug(f'External remote address set to {config.external_address}')

    verify_docker()
    configure_docker_gid(config)
    generate_secrets(config)

    plugins_path = Path('.plugins')
    if not plugins_path.is_dir():
        logger.info('Creating plugins volume…')
        plugins_path.mkdir(parents=True, exist_ok=True)
        plugins_path.chmod(0o777)
        metrics_path = plugins_path / 'metrics'
        metrics_path.mkdir(parents=True, exist_ok=True)
        metrics_path.chmod(0o777)

    logger.info('Templating config files…')
    render_vars = {
        'DOCKER_GID': config.docker_gid,
        'PUB_AUTH_TOKEN': config.pub_auth_token,
        'IMAGE_BUILDER_AUTH_TOKEN': config.image_builder_auth_token,
        'POSTGRES_PASSWORD': config.postgres_password,
        'AUTH_KEY': config.auth_key,
        'SECRET_KEY': config.django_secret_key,
        'EXTERNAL_ADDRESS': config.external_address,
    }
    template_repository_file('utils/standalone-wizard/docker/docker-compose.template.yaml', 'docker-compose.yaml', render_vars)
    template_repository_file('utils/standalone-wizard/docker/.env.template', '.env', render_vars)
    template_repository_file('utils/standalone-wizard/docker/lifecycle.template.yaml', 'config/lifecycle.yaml', render_vars)
    download_repository_file('utils/standalone-wizard/docker/Makefile', 'Makefile')
    download_repository_file('image_builder/tests/sample/compose.yaml', 'config/image_builder.yaml')
    download_repository_file('postgres/init.sql', 'config/postgres/init.sql')
    download_repository_file('utils/prometheus/prometheus.yaml', 'utils/prometheus/prometheus.yaml')
    download_repository_file('utils/grafana/datasource.yaml', 'utils/grafana/datasource.yaml')
    download_repository_file('utils/grafana/dashboards-all.yaml', 'utils/grafana/dashboards-all.yaml')
    for dashboard in GRAFANA_DASHBOARDS:
        download_repository_file(f'utils/grafana/dashboards/{dashboard}.json', f'utils/grafana/dashboards/{dashboard}.json')
    download_repository_file('sample/python-class/adder.py', 'sample/python-class/adder.py')
    download_repository_file('sample/python-class/job.yaml', 'sample/python-class/job.yaml')

    logger.info('Starting up containers…')
    shell('DOCKER_BUILDKIT=1 DOCKER_SCAN_SUGGEST=false docker compose up -d --no-build --pull=always --wait', raw_output=True)

    logger.info('Waiting until Racetrack is operational (usually it takes 30s)…')
    wait_for_lifecycle('http://127.0.0.1:7102')

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


def install_to_kubernetes(config: 'SetupConfig'):
    logger.info('Installing Racetrack to Kubernetes')

    config.registry_hostname = ensure_var_configured(
        config.registry_hostname, 'registry_hostname', 'ghcr.io',
        'Enter Docker registry hostname (to keep the job images)')
    config.registry_namespace = ensure_var_configured(
        config.registry_namespace, 'registry_namespace', 'theracetrack/racetrack',
        'Enter Docker registry namespace')
    config.registry_username = ensure_var_configured(
        config.registry_username, 'registry_username', 'racetrack-registry',
        'Enter Docker registry username')
    config.read_registry_token = ensure_var_configured(
        config.read_registry_token, 'read_registry_token', '',
        'Enter token for reading from Docker Registry')
    config.write_registry_token = ensure_var_configured(
        config.write_registry_token, 'write_registry_token', '',
        'Enter token for writing to Docker Registry')
    config.public_ip = ensure_var_configured(
        config.public_ip, 'public_ip', '',
        'Enter your IP address for all public services exposed by Ingress, e.g. 1.1.1.1')
    save_local_config(config)

    try:
        shell('kubectl config get-contexts')
    except CommandError as e:
        logger.error('kubectl is unavailable.')
        raise e
    kubectl_context = shell_output('kubectl config current-context').strip()
    logger.info(f'Current kubectl context is {kubectl_context}')
    shell_output('kubectl config set-context --current --namespace=racetrack')

    generate_secrets(config)

    generated_dir = get_generated_dir()
    registry_secrets_content = shell_output(f'''kubectl create secret docker-registry docker-registry-read-secret \\
        --docker-server="{config.registry_hostname}" \\
        --docker-username="{config.registry_username}" \\
        --docker-password="{config.read_registry_token}" \\
        --namespace=racetrack \\
        --dry-run=client -oyaml''').strip()
    registry_secrets_content += '\n---\n'
    registry_secrets_content += shell_output(f'''kubectl create secret docker-registry docker-registry-write-secret \\
        --docker-server="{config.registry_hostname}" \\
        --docker-username="{config.registry_username}" \\
        --docker-password="{config.write_registry_token}" \\
        --namespace=racetrack \\
        --dry-run=client -oyaml''').strip()
    registry_secrets_file = generated_dir / 'docker-registry-secret.yaml'
    registry_secrets_file.write_text(registry_secrets_content)
    logger.debug(f"encoded Docker registry secrets: {registry_secrets_file}")

    render_vars = {
        'POSTGRES_PASSWORD': config.postgres_password,
        'SECRET_KEY': config.django_secret_key,
        'AUTH_KEY': config.auth_key,
        'public_ip': config.public_ip,
        'registry_hostname': config.registry_hostname,
        'registry_namespace': config.registry_namespace,
        'IMAGE_BUILDER_TOKEN': config.image_builder_auth_token,
        'PUB_TOKEN': config.pub_auth_token,
    }
    template_files = [
        'dashboard.yaml',
        'grafana.yaml',
        'image-builder.config.yaml',
        'image-builder.yaml',
        'ingress.yaml',
        'ingress-controller.yaml',
        'kustomization.yaml',
        'lifecycle.config.yaml',
        'lifecycle.env',
        'lifecycle.yaml',
        'lifecycle-supervisor.yaml',
        'namespace.yaml',
        'pgbouncer.env',
        'postgres.env',
        'postgres.yaml',
        'priorities.yaml',
        'prometheus.yaml',
        'pub.yaml',
        'roles.yaml',
        'volumes.yaml',
        'config/grafana/datasource.yaml',
        'config/grafana/dashboards-all.yaml',
        'config/prometheus/prometheus.yaml',
    ]
    for template_file in template_files:
        template_repository_file(f'utils/standalone-wizard/kubernetes/{template_file}', f'generated/{template_file}', render_vars)
    logger.info(f'Kubernetes resources created at "{generated_dir.absolute()}". Please review them before applying.')

    cmd = f'kubectl apply -k {generated_dir}/'
    if prompt_bool(f'Attempting to execute command "{cmd}". Do you confirm?'):
        shell(cmd, raw_output=True)
        logger.info("Racetrack has been deployed.")


def install_to_remote_docker(config: 'SetupConfig'):
    logger.info('Installing Jobs gateway to remote Docker Daemon')

    config.registry_hostname = ensure_var_configured(
        config.registry_hostname, 'registry_hostname', 'ghcr.io',
        'Enter Docker registry hostname (to keep the job images)')
    config.registry_username = ensure_var_configured(
        config.registry_username, 'registry_username', 'racetrack-registry',
        'Enter Docker registry username')
    config.write_registry_token = ensure_var_configured(
        config.write_registry_token, 'write_registry_token', '',
        'Enter token for writing to Docker Registry')
    config.public_ip = ensure_var_configured(
        config.public_ip, 'public_ip', '',
        'Enter IP address of your infrastructure target, e.g. 1.1.1.1')
    config.remote_gateway_config.pub_remote_image = ensure_var_configured(
        config.remote_gateway_config.pub_remote_image, 'pub_remote_image', 'ghcr.io/theracetrack/plugin-remote-docker/pub-remote:latest',
        'Enter name of the Docker image of remote Pub')

    if not config.remote_gateway_config.remote_gateway_token:
        config.remote_gateway_config.remote_gateway_token = generate_password()
        logger.info(f'Generated remote gateway token: {config.remote_gateway_config.remote_gateway_token}')
    save_local_config(config)

    verify_docker()
    configure_docker_gid(config)

    docker_vol_dir = Path('.docker')
    if not docker_vol_dir.is_dir():
        logger.info('Creating .docker volume…')
        docker_vol_dir.mkdir(parents=True, exist_ok=True)
        docker_vol_dir.chmod(0o777)

    logger.debug('Creating "racetrack_default" docker network…')
    labels = '--label com.docker.compose.network=racetrack_default racetrack_default --label com.docker.compose.project=wizard'
    shell(f'docker network create {labels} || true')
    shell(f'docker pull {config.remote_gateway_config.pub_remote_image}')
    logger.debug('Creating pub-remote container…')
    shell('docker rm -f pub-remote || true')

    cmd = f'''docker run -d \
--name=pub-remote \
--user=100000:{config.docker_gid} \
--env=AUTH_REQUIRED=true \
--env=AUTH_DEBUG=true \
--env=PUB_PORT=7105 \
--env=REMOTE_GATEWAY_MODE=true \
--env=REMOTE_GATEWAY_TOKEN="{config.remote_gateway_config.remote_gateway_token}" \
-p 7105:7105 \
--volume "/var/run/docker.sock:/var/run/docker.sock" \
--volume "{docker_vol_dir.absolute()}:/.docker" \
--restart=unless-stopped \
--network="racetrack_default" \
--add-host host.docker.internal:host-gateway \
{config.remote_gateway_config.pub_remote_image}'''
    if prompt_bool(f'Attempting to execute command: {cmd}\nDo you confirm?'):
        shell(cmd)
        logger.info("Remote Pub Gateway is ready.")

    template_repository_file('utils/standalone-wizard/remote-docker/plugin-config.yaml', 'plugin-config.yaml', {
        'public_ip': config.public_ip,
        'remote_gateway_token': config.remote_gateway_config.remote_gateway_token,
        'registry_hostname': config.registry_hostname,
        'registry_username': config.registry_username,
        'write_registry_token': config.write_registry_token,
    })
    logger.info("Configure remote-docker plugin with the following configuration:")
    print(Path('plugin-config.yaml').read_text())


def install_to_remote_kubernetes(config: 'SetupConfig'):
    logger.info('Installing Jobs gateway to remote Kubernetes')

    config.registry_hostname = ensure_var_configured(
        config.registry_hostname, 'registry_hostname', 'ghcr.io',
        'Enter Docker registry hostname (to keep the job images)')
    config.registry_username = ensure_var_configured(
        config.registry_username, 'registry_username', 'racetrack-registry',
        'Enter Docker registry username')
    config.read_registry_token = ensure_var_configured(
        config.read_registry_token, 'read_registry_token', '',
        'Enter token for reading from Docker Registry')
    config.write_registry_token = ensure_var_configured(
        config.write_registry_token, 'write_registry_token', '',
        'Enter token for writing to Docker Registry')
    config.public_ip = ensure_var_configured(
        config.public_ip, 'public_ip', '',
        'Enter IP address of your infrastructure target, e.g. 1.1.1.1')
    config.remote_gateway_config.pub_remote_image = ensure_var_configured(
        config.remote_gateway_config.pub_remote_image, 'pub_remote_image', 'ghcr.io/theracetrack/plugin-remote-kubernetes/pub-remote:latest',
        'Enter name of the Docker image of remote Pub')
    config.kubernetes_namespace = ensure_var_configured(
        config.kubernetes_namespace, 'kubernetes_namespace', 'racetrack',
        'Enter namespace for the Kubernetes resources')

    if not config.remote_gateway_config.remote_gateway_token:
        config.remote_gateway_config.remote_gateway_token = generate_password()
        logger.info(f'Generated remote gateway token: {config.remote_gateway_config.remote_gateway_token}')
    save_local_config(config)

    generated_dir = get_generated_dir()
    registry_secrets_content = shell_output(f'''kubectl create secret docker-registry docker-registry-read-secret \\
        --docker-server="{config.registry_hostname}" \\
        --docker-username="{config.registry_username}" \\
        --docker-password="{config.read_registry_token}" \\
        --namespace=racetrack \\
        --dry-run=client -oyaml''').strip()
    registry_secrets_file = generated_dir / 'docker-registry-secret.yaml'
    registry_secrets_file.write_text(registry_secrets_content)
    logger.debug(f"Docker registry secret encoded at {registry_secrets_file}")

    render_vars = {
        'NAMESPACE': config.kubernetes_namespace,
        'PUB_REMOTE_IMAGE': config.remote_gateway_config.pub_remote_image,
        'REMOTE_GATEWAY_TOKEN': config.remote_gateway_config.remote_gateway_token,
        'public_ip': config.public_ip,
        'remote_gateway_token': config.remote_gateway_config.remote_gateway_token,
        'kubernetes_namespace': config.kubernetes_namespace,
        'registry_hostname': config.registry_hostname,
        'registry_username': config.registry_username,
        'write_registry_token': config.write_registry_token,
    }
    if prompt_bool('Would you like to create a namespace in kubernetes for Racetrack resources?'):
        template_repository_file('utils/standalone-wizard/remote-kubernetes/namespace.yaml', 'generated/namespace.yaml', render_vars)

    if prompt_bool('Would you like to configure roles so that pods can speak to local Kubernetes API inside the cluster?'):
        template_repository_file('utils/standalone-wizard/remote-kubernetes/roles.yaml', 'generated/roles.yaml', render_vars)

    if prompt_bool('Would you like to configure Ingress and Ingress Controller to direct incoming traffic?'):
        download_repository_file('utils/standalone-wizard/remote-kubernetes/ingress-controller.yaml', 'generated/ingress-controller.yaml')
        template_repository_file('utils/standalone-wizard/remote-kubernetes/ingress.yaml', 'generated/ingress.yaml', render_vars)

    template_repository_file('utils/standalone-wizard/remote-kubernetes/remote-pub.yaml', 'generated/remote-pub.yaml', render_vars)
    logger.info(f'Kubernetes resources created at "{generated_dir.absolute()}". Please review them before applying.')

    cmd = f'kubectl apply -f {generated_dir}'
    if prompt_bool(f'Attempting to execute command "{cmd}". Do you confirm?'):
        shell(cmd, raw_output=True)
        logger.info("Remote Pub Gateway is ready.")

    template_repository_file('utils/standalone-wizard/remote-kubernetes/plugin-config.yaml', 'plugin-config.yaml', render_vars)
    logger.info("Configure remote-kubernetes plugin with the following configuration:")
    print(Path('plugin-config.yaml').read_text())


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
    admin_password: str = ''
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
    logger.debug(f'Downloading {src_file_url}')
    with urllib.request.urlopen(src_file_url) as response:
        src_content: bytes = response.read()
    template = string.Template(src_content.decode())
    outcome: str = template.substitute(**context_vars)
    dst_file = Path(dst_path)
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    dst_file.write_text(outcome)


def download_repository_file(src_relative_url: str, dst_path: Union[str, Path]):
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


def get_generated_dir() -> Path:
    generated_dir = Path('generated')
    if generated_dir.exists():
        if prompt_bool(f'Directory "{generated_dir}" already exists. Would you like to clear it?'):
            logger.info(f'cleaning up directory "{generated_dir}"')
            shutil.rmtree(generated_dir)
    generated_dir.mkdir(parents=True, exist_ok=True)
    return generated_dir


def wait_for_lifecycle(url: str, attempts: int = 30):
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


if __name__ == '__main__':
    main()
