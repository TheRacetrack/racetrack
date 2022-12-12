from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import backoff

from racetrack_client.log.context_error import wrap_context
from racetrack_client.utils.semver import SemanticVersion
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine


@dataclass
class JobType:
    lang_name: str
    version: str  # semantic version of the job type
    base_image_path: Path  # base Dockerfile path
    template_path: Path  # fatman template Dockerfile path


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

    plugin_results: list[dict[str, tuple[Path, Path]]] = plugin_engine.invoke_plugin_hook(PluginCore.fatman_job_types)
    for plugin_job_types in plugin_results:
        if plugin_job_types:
            for job_full_name, job_data in plugin_job_types.items():
                base_image_path, template_path = job_data
                assert base_image_path.is_file(), f'cannot find base image Dockerfile for {job_full_name} language wrapper: {base_image_path}'
                assert template_path.is_file(), f'cannot find Dockerfile template for {job_full_name} language wrapper: {template_path}'
                name_parts = job_full_name.split(':')
                assert len(name_parts) == 2, f'job type {job_full_name} should have the version defined (name:version)'
                lang_name = name_parts[0]
                lang_version = name_parts[1]
                job_type_version = JobType(lang_name, lang_version, base_image_path, template_path)
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
