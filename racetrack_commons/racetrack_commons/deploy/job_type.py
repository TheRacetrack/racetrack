from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

import backoff

from racetrack_client.log.context_error import wrap_context
from racetrack_client.utils.semver import SemanticVersion, SemanticVersionPattern
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.plugin.plugin_data import PluginData


@dataclass
class JobType:
    lang_name: str
    version: str  # semantic version of the job type
    template_paths: list[str]  # relative path names to job template Dockerfiles (for each container)
    jobtype_dir: Path
    base_image_paths: list[Path]  # Deprecated

    @property
    def full_name(self) -> str:
        return f'{self.lang_name}:{self.version}'

    @property
    def containers_num(self) -> int:
        return len(self.template_paths)


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
    all_languages = sorted(job_types.keys())
    selected_version = match_job_type_version(lang, all_languages)
    job_type = job_types[selected_version]
    _validate_job_type(job_type)
    return job_type


def match_job_type_version(lang: str, all_languages: list[str]) -> str:
    """
    Find job type by either:
    - exact name and version
    - wildcard pattern with "*"
    - latest tag: "name:latest"
    """
    lang_split = lang.split(':')
    assert len(lang_split) == 2, f'job type should be specified as "name:version", got "{lang}"'
    lang_name = lang_split[0]
    lang_version = lang_split[1]

    if lang_version == 'latest':
        lang_versions = [v.split(':')[1] for v in all_languages if v.startswith(lang_name + ':')]
        lang_versions.sort(key=lambda v: SemanticVersion(v))
        assert lang_versions, f'there is no version matching "{lang}", supported are: {all_languages}'
        latest_version = lang_versions[-1]
        return f'{lang_name}:{latest_version}'
            
    elif SemanticVersionPattern.is_asterisk_pattern(lang_version):
        lang_versions = [v.split(':')[1] for v in all_languages if v.startswith(lang_name + ':')]
        version_pattern = SemanticVersionPattern.from_asterisk_pattern(lang_version)
        matching_version = SemanticVersion.find_latest_wildcard(version_pattern, lang_versions, key=lambda v: v, only_stable=False)
        assert matching_version is not None, f'language pattern "{lang}" doesn\'t match any of the supported versions: {all_languages}'
        return f'{lang_name}:{matching_version}'

    else:
        assert lang in all_languages, f'language {lang} is not supported, supported are: {all_languages}'
        return lang
    

def gather_job_types(
    plugin_engine: PluginEngine,
) -> dict[str, JobType]:
    """
    Load job types from plugins.
    Return dictionary: job name (with version) mapped to JobType data
    """
    job_types: dict[str, JobType] = {}

    plugin_data: PluginData
    plugin_job_types: dict[str, list[str | Path]]
    for plugin_data, plugin_job_types in plugin_engine.invoke_hook_with_origin(PluginCore.job_types):
        if not plugin_job_types:
            continue

        for job_type_key, job_type_value in plugin_job_types.items():

            template_paths: list[str]
            base_image_paths: list[Path] = []  # Deprecated, kept for backwards compatibility
            if isinstance(job_type_value, list):
                if all(isinstance(item, tuple) for item in job_type_value):
                    base_image_paths = [Path(item[0]) for item in job_type_value]
                    template_paths = [Path(item[1]).as_posix() for item in job_type_value]
                else:
                    for item in job_type_value:
                        assert isinstance(item, str), f'Invalid dockerfile template path of a job type. Expected str, but found {type(item)}'
                    template_paths = job_type_value
            elif isinstance(job_type_value, str):
                template_paths = [job_type_value]
            elif isinstance(job_type_value, tuple):
                base_image_paths = [Path(job_type_value[0])]
                template_paths = [Path(job_type_value[1]).as_posix()]
            else:
                raise RuntimeError(f'Invalid job type data. Expected list[str], was {type(job_type_value)}')
            assert len(template_paths) > 0, 'list of job type template paths can not be empty'

            name_parts = job_type_key.split(':')
            assert len(name_parts) == 2, f'job type {job_type_key} should have the version defined (name:version)'
            lang_name = name_parts[0]
            lang_version = name_parts[1]
            job_type_version = JobType(
                lang_name=lang_name,
                version=lang_version,
                template_paths=template_paths,
                jobtype_dir=plugin_data.plugin_dir,
                base_image_paths=base_image_paths,
            )
            job_types[job_type_key] = job_type_version

    return job_types


def _validate_job_type(job_type: JobType):
    template_paths: list[str] = job_type.template_paths
    job_full_name: str = job_type.full_name
    assert len(template_paths) > 0, 'Job type should have non-empty list of template images'

    for i, template_path in enumerate(template_paths):
        if template_path is not None:
            template_full_path = job_type.jobtype_dir / template_path
            assert template_full_path.is_file(), f'cannot find Dockerfile template for {job_full_name} job type: {template_full_path}'
