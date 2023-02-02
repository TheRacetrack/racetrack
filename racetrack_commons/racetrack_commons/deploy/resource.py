def job_resource_name(job.name: str, job.version: str) -> str:
    """
    Assemble internal resource name inside a cluster for a particular Job.
    The name of a Service object must be a valid RFC 1035 label name.
    """
    return f'job-{job.name}-v-{job.version}'.replace('.', '-')
