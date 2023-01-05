from racetrack_client.utils.url import join_paths


def get_fatman_image(docker_registry: str, registry_namespace: str, name: str, tag: str, image_index: int = 0) -> str:
    """
    Return full name of Fatman image.
    If a fatman is composed of multiple containers / images, the index number of the module is included.
    Image with `image_index` number equal 0 is the first entrypoint of the Fatman.
    Higher index numbers refer to other, auxiliary images being a part of the Fatman.
    """
    if image_index == 0:
        image_type = 'fatman-entrypoint'
    else:
        image_type = f'fatman-{image_index}'
    return join_paths(docker_registry, registry_namespace, image_type, f'{name}:{tag}')
