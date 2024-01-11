from pathlib import Path

from jinja2 import Template

from racetrack_commons.deploy.resource import job_resource_name
from racetrack_client.manifest import Manifest


def template_dockerfile(
    manifest: Manifest,
    template_path: Path,
    dockerfile_path: Path,
    git_version: str,
    racetrack_version: str | None,
    job_type_version: str | None,
    env_vars: dict[str, str],
    base_image: str | None = None,
):
    """
    Create Dockerfile from Jinja template and manifest data
    :param manifest: Job manifest data
    :param template_path: Path to Jinja template file
    :param dockerfile_path: Path to output Dockerfile that will be created from template
    :param git_version: version name from Job git history
    :param racetrack_version: Version of Racetrack the Job was deployed with
    :param job_type_version: Version of Job Type used to build the Job's image
    :param env_vars: environment variables that should be set during building
    :param base_image: (Deprecated) name of the base docker image
    """
    template_content = Path(template_path).read_text()
    template = Template(template_content)
    resource_name = job_resource_name(manifest.name, manifest.version)
    render_vars = {
        'manifest': manifest,
        'base_image': base_image,
        'resource_name': resource_name,
        'git_version': git_version,
        'deployed_by_racetrack_version': racetrack_version,
        'job_type_version': job_type_version,
        'env_vars': env_vars,
    }
    templated = template.render(**render_vars)
    Path(dockerfile_path).write_text(templated)
