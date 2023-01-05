def fatman_resource_name(fatman_name: str, fatman_version: str) -> str:
    """
    Assemble internal resource name inside a cluster for a particular Fatman.
    The name of a Service object must be a valid RFC 1035 label name.
    """
    return f'fatman-{fatman_name}-v-{fatman_version}'.replace('.', '-')
