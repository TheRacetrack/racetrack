import os

    
def get_external_pub_url(default_pub_url: str = '') -> str:
    """Build external URL where PUB can be accessed at outside of the cluster"""
    cluster_domain = os.environ.get('CLUSTER_FQDN')
    if cluster_domain:
        racetrack_subdomain = os.environ.get('RACETRACK_SUBDOMAIN', 'racetrack')
        return f'https://{racetrack_subdomain}.{cluster_domain}/pub'
    if not default_pub_url:
        default_pub_url = os.environ.get('EXTERNAL_PUB_URL', '')
        if not default_pub_url:
            return 'default external pub url was not set'
    return f'{default_pub_url}'


def get_external_lifecycle_url() -> str:
    """Build external URL where Lifecycle can be accessed at outside of the cluster"""
    cluster_domain = os.environ.get('CLUSTER_FQDN')
    if cluster_domain:
        racetrack_subdomain = os.environ.get('RACETRACK_SUBDOMAIN', 'racetrack')
        return f'https://{racetrack_subdomain}.{cluster_domain}/lifecycle'
    external_lifecycle_url = os.environ.get('EXTERNAL_LIFECYCLE_URL')
    if not external_lifecycle_url:
        return 'neither CLUSTER_FQDN nor EXTERNAL_LIFECYCLE_URL has been set'
    return f'{external_lifecycle_url}'
