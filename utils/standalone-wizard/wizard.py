#!/usr/bin/env python3
from pathlib import Path

import sys

from racetrack_client.log.logs import configure_logs
from racetrack_client.utils.shell import shell_output, CommandError
from utils import logger, SetupConfig, load_local_config, prompt_text_choice, prompt_text, save_local_config, \
    verify_docker, configure_docker_gid, generate_secrets, template_repository_file, download_repository_file, shell, \
    wait_for_lifecycle, login_first_time, ensure_var_configured, get_generated_dir, prompt_bool, generate_password


def main():
    configure_logs(log_level='debug')
    logger.info('Welcome to the standalone Racetrack installer')

    if sys.version_info[:2] < (3, 8):
        logger.warning(f'This installer requires Python 3.8 or higher, but found: {sys.version_info}')

    config: SetupConfig = load_local_config()
    try:
        install_racetrack(config)
    except KeyboardInterrupt:
        print()


def install_racetrack(config: 'SetupConfig'):
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
        if not config.external_address.startswith('http'):
            config.external_address = 'http://' + config.external_address
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
    download_repository_file('utils/cleanup-jobs-docker.sh', 'cleanup-jobs-docker.sh')
    download_repository_file('image_builder/tests/sample/compose.yaml', 'config/image_builder.yaml')
    download_repository_file('postgres/init.sql', 'config/postgres/init.sql')
    download_repository_file('utils/prometheus/prometheus.yaml', 'utils/prometheus/prometheus.yaml')
    download_repository_file('utils/grafana/datasource.yaml', 'utils/grafana/datasource.yaml')
    download_repository_file('utils/grafana/dashboards-all.yaml', 'utils/grafana/dashboards-all.yaml')
    grafana_dashboards = ['image-builder', 'jobs', 'lifecycle', 'postgres', 'pub']
    for dashboard in grafana_dashboards:
        download_repository_file(f'utils/grafana/dashboards/{dashboard}.json', f'utils/grafana/dashboards/{dashboard}.json')
    download_repository_file('sample/python-class/adder.py', 'sample/python-class/adder.py')
    download_repository_file('sample/python-class/job.yaml', 'sample/python-class/job.yaml')

    logger.info('Starting up containers…')
    shell('DOCKER_BUILDKIT=1 DOCKER_SCAN_SUGGEST=false docker compose up -d --no-build --pull=always --wait', raw_output=True)

    logger.info('Waiting until Racetrack is operational (usually it takes 30s)…')
    lifecycle_url = 'http://127.0.0.1:7102'
    wait_for_lifecycle(lifecycle_url)
    login_first_time(config, lifecycle_url)
    logger.info('Installing plugins…')
    shell('python -m racetrack_client plugin install github.com/TheRacetrack/plugin-python-job-type')
    shell('python -m racetrack_client plugin install github.com/TheRacetrack/plugin-docker-infrastructure')

    logger.info(f'''Racetrack is ready to use.
Visit Racetrack Dashboard at {config.external_address}:7103/dashboard
Log in with username: admin, password: {config.admin_password}
Your Racetrack Auth Token (X-Racetrack-Auth): {config.admin_auth_token}
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

    logger.info('Waiting until Racetrack is operational…')
    lifecycle_url = f'http://{config.public_ip}/lifecycle'
    wait_for_lifecycle(lifecycle_url)
    login_first_time(config, lifecycle_url)

    logger.info('Installing plugins…')
    shell('python -m racetrack_client plugin install github.com/TheRacetrack/plugin-python-job-type')
    shell('python -m racetrack_client plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure')

    logger.info(f'''Racetrack is ready to use.
Visit Racetrack Dashboard at http://{config.public_ip}/dashboard
Log in with username: admin, password: {config.admin_password}
Your Racetrack Auth Token (X-Racetrack-Auth): {config.admin_auth_token}
To deploy here, configure your racetrack client: racetrack set remote {lifecycle_url}
''')


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
    shell(f'docker network create {labels} || true', print_stdout=False)

    shell(f'docker pull {config.remote_gateway_config.pub_remote_image}')
    if shell_output('docker ps -aq -f name=^pub-remote$').strip():
        logger.debug('Deleting old pub-remote container…')
        shell('docker rm -f pub-remote')

    logger.debug('Creating pub-remote container…')
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


if __name__ == '__main__':
    main()
