from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import backoff

from racetrack_client.log.context_error import wrap_context
from racetrack_client.utils.semver import SemanticVersion
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine


JobTypeImagePaths = Union[list[tuple[Path, Path]], tuple[Path, Path]]


@dataclass
class JobType:
    lang_name: str
    version: str  # semantic version of the job type
    base_image_paths: list[Path]  # paths to base Dockerfiles (for each container)
    template_paths: list[Path]  # paths to job template Dockerfiles (for each container)


@backoff.on_exception(backoff.fibo, AssertionError, max_value=1, max_time=5, jitter=None, logger=None)
def load_job_type(
    plugin_engine: PluginEngine,
    lang: str,
) -> JobType:
    """
    Load job type.
    In case it's not found, retry attempts due to possible delayed plugins loading
    """
    with wrap_context('gathering available job types'):
        job_types = gather_job_types(plugin_engine)
    assert job_types, f'language {lang} is not supported here. No job type plugins are currently installed to Racetrack.'
    assert lang in job_types, f'language {lang} is not supported, supported are: {sorted(job_types.keys())}'
    return job_types[lang]


def gather_job_types(
    plugin_engine: PluginEngine,
) -> dict[str, JobType]:
    """
    Load job types from plugins.
    Return job name (with version) -> (base image name, dockerfile template path)
    """
    job_types: dict[str, JobType] = {}
    job_family_versions: dict[str, list[JobType]] = defaultdict(list)

    plugin_results: list[dict[str, JobTypeImagePaths]] = plugin_engine.invoke_plugin_hook(PluginCore.job_types)
    for plugin_job_types in plugin_results:
        if plugin_job_types:
            for job_full_name, job_data in plugin_job_types.items():

                if isinstance(job_data, tuple):
                    base_image_paths = [job_data[0]]
                    template_paths = [job_data[1]]
                elif isinstance(job_data, list):
                    base_image_paths = [item[0] for item in job_data]
                    template_paths = [item[1] for item in job_data]
                else:
                    raise RuntimeError(f'Invalid job type data. It should be list[tuple[Path, Path]], was {type(job_data)}')

                _validate_dockerfile_paths(base_image_paths, template_paths, job_full_name)

                name_parts = job_full_name.split(':')
                assert len(name_parts) == 2, f'job type {job_full_name} should have the version defined (name:version)'
                lang_name = name_parts[0]
                lang_version = name_parts[1]
                job_type_version = JobType(lang_name, lang_version, base_image_paths, template_paths)
                job_types[job_full_name] = job_type_version
                job_family_versions[lang_name].append(job_type_version)

    for lang_name in job_family_versions.keys():
        versions = job_family_versions[lang_name]
        versions.sort(key=lambda v: SemanticVersion(v.version))
        latest_version = versions[-1]
        job_types[f'{lang_name}:latest'] = latest_version

    return job_types


def list_available_job_types(plugin_engine: PluginEngine) -> list[str]:
    with wrap_context('gathering available job types'):
        job_types = gather_job_types(plugin_engine)
    return sorted(job_types.keys())


def _validate_dockerfile_paths(base_image_paths: list[Path], template_paths: list[Path], job_full_name: str):
    assert len(base_image_paths) > 0, 'Job type should have non-empty list of base images'

    for i, base_image_path in enumerate(base_image_paths):
        template_path = template_paths[i]
        if base_image_path is not None:
            assert base_image_path.is_file(), f'cannot find base image Dockerfile for {job_full_name} language wrapper: {base_image_path}'
        if template_path is not None:
            assert template_path.is_file(), f'cannot find Dockerfile template for {job_full_name} language wrapper: {template_path}'
