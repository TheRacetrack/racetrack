def job_resource_name(job_name: str, job_version: str) -> str:
    """
    Assemble internal resource name inside a cluster for a particular Job.
    The name of a Service object must be a valid RFC 1035 label name.
    """
    return f'job-{job_name}-v-{job_version}'.replace('.', '-')
