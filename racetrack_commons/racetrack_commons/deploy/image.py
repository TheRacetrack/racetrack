from racetrack_client.utils.url import join_paths


def get_fatman_image(docker_registry: str, registry_namespace: str, name: str, tag: str, module_index: int = 0) -> str:
    """
    Return full name of Fatman image.
    If a fatman is composed of multiple containers, the module number is included.
    """
    if module_index == 0:
        image_type = 'fatman-entrypoint'
    else:
        image_type = f'fatman-{module_index}'
    return join_paths(docker_registry, registry_namespace, image_type, f'{name}:{tag}')
