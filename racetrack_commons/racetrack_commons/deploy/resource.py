def fatman_resource_name(fatman_name: str, fatman_version: str) -> str:
    """
    Assemble internal resource name inside a cluster for a particular Fatman.
    The name of a Service object must be a valid RFC 1035 label name.
    """
    return f'fatman-{fatman_name}-v-{fatman_version}'.replace('.', '-')


def fatman_user_module_resource_name(fatman_name: str, fatman_version: str) -> str:
    """Assemble resource name of Fatman's user module (user-defined container for Dockerfile job type)"""
    base_resource_name = fatman_resource_name(fatman_name, fatman_version)
    return f'{base_resource_name}-user-module'
