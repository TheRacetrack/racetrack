from pathlib import Path
from typing import Optional, Dict

from jinja2 import Template

from racetrack_commons.deploy.resource import job_resource_name
from racetrack_client.manifest import Manifest


def template_dockerfile(
    manifest: Manifest,
    template_path: Path,
    dockerfile_path: Path,
    base_image: Optional[str],
    git_version: str,
    deployed_by_racetrack_version: Optional[str],
    job_type_version: Optional[str],
    env_vars: Dict[str, str],
):
    """
    Create Dockerfile from Jinja template and manifest data
    :param manifest: Job manifest data
    :param template_path: Path to Jinja template file
    :param dockerfile_path: Path to output Dockerfile that will be created from template
    :param base_image: Full name of base image
    :param git_version: version name from Job git history
    :param deployed_by_racetrack_version: Version of Racetrack the Job was deployed with
    :param job_type_version: Version of Job Type used to build the Job's image
    :param env_vars: environment variables that should be set during building
    """
    template_content = Path(template_path).read_text()
    template = Template(template_content)
    resource_name = job_resource_name(manifest.name, manifest.version)
    render_vars = {
        'manifest': manifest,
        'base_image': base_image,
        'resource_name': resource_name,
        'git_version': git_version,
        'deployed_by_racetrack_version': deployed_by_racetrack_version,
        'job_type_version': job_type_version,
        'env_vars': env_vars,
    }
    templated = template.render(**render_vars)
    Path(dockerfile_path).write_text(templated)
