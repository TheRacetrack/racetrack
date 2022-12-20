from racetrack_client.utils.url import join_paths


def get_full_image(
    docker_registry: str,
    docker_registry_namespace: str,
    image_type: str,
    name: str,
    tag: str,
) -> str:
    """Return full docker image name"""
    return join_paths(docker_registry, docker_registry_namespace, image_type, f'{name}:{tag}')


def get_fatman_base_image(docker_registry: str, registry_namespace: str, name: str, tag: str, module_index: int = 0) -> str:
    """Return full name of Fatman base image"""
    if module_index == 0:
        image_type = 'fatman-base'
    else:
        image_type = f'fatman-base-{module_index}'
    return join_paths(docker_registry, registry_namespace, image_type, f'{name}:{tag}')


def get_fatman_image(docker_registry: str, registry_namespace: str, name: str, tag: str, module_index: int = 0) -> str:
    """Return full name of Fatman entrypoint image"""
    if module_index == 0:
        image_type = 'fatman-entrypoint'
    else:
        image_type = f'fatman-entrypoint-{module_index}'
    return join_paths(docker_registry, registry_namespace, image_type, f'{name}:{tag}')


def get_fatman_user_module_image(docker_registry: str, registry_namespace: str, name: str, tag: str) -> str:
    """Return full name of Fatman user-module image (from Dockerfile job type)"""
    return get_full_image(docker_registry, registry_namespace, 'fatman-user-module', name, tag)


def get_fatman_module_image(docker_registry: str, registry_namespace: str, module_index: int, name: str, tag: str) -> str:
    """Return full name of Fatman submodule image in case of fatman composed of multiple containers"""
    if module_index == 0:
        image_type = 'fatman-entrypoint'
    else:
        image_type = f'fatman-entrypoint-{module_index}'
    return join_paths(docker_registry, registry_namespace, image_type, f'{name}:{tag}')
