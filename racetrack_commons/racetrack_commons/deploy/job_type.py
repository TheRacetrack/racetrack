from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

import backoff

from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_client.utils.semver import SemanticVersion, SemanticVersionPattern
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.plugin.plugin_data import PluginData

logger = get_logger(__name__)


@dataclass
class JobTypeImageDef:
    source: str  # either 'jobtype' or 'job' depending on location of the Dockerfile
    dockerfile_path: Path  # absolute path to job image Dockerfile template
    template: bool  # whether Dockerfile is a template and contains variables to evaluate
    base_image_path: Path | None = None  # Deprecated: absolute path to base Dockerfile


@dataclass
class JobType:
    lang_name: str
    version: str  # semantic version of the job type
    images: list[JobTypeImageDef]
    jobtype_dir: Path
    plugin_data: PluginData

    @property
    def full_name(self) -> str:
        return f'{self.lang_name}:{self.version}'

    @property
    def images_num(self) -> int:
        return len(self.images)


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
        matching_version = SemanticVersion.find_latest_wildcard(version_pattern, lang_versions, key=lambda v: v,
                                                                only_stable=False)
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

        assert isinstance(plugin_job_types, dict), '"job_types" returned by plugins should be a dictionary'
        for job_type_key, job_type_value in plugin_job_types.items():
            job_types[job_type_key] = _parse_job_type_definition(job_type_key, job_type_value, plugin_data)

    return job_types


def _parse_job_type_definition(
    job_type_key: str,
    job_type_value: dict | list | str | tuple,
    plugin_data: PluginData,
) -> JobType:
    name_parts = job_type_key.split(':')
    assert len(name_parts) == 2, f'job type {job_type_key} should have the version defined in a format "name:version"'
    lang_name = name_parts[0]
    lang_version = name_parts[1]

    job_type = JobType(
        lang_name=lang_name,
        version=lang_version,
        images=[],
        jobtype_dir=plugin_data.plugin_dir,
        plugin_data=plugin_data,
    )

    if isinstance(job_type_value, dict):
        images_dicts: list[dict] = job_type_value.get('images', [])
        for images_dict in images_dicts:
            source: str = images_dict.get('source', 'jobtype')
            assert source in {'jobtype', 'job'}, "'source' can be either 'jobtype' or 'job'"
            dockerfile_path_str: str = images_dict.get('dockerfile_path')
            assert dockerfile_path_str, '"dockerfile_path" is not specified in job type data'
            dockerfile_path = Path(dockerfile_path_str)
            if source == 'jobtype':
                dockerfile_path = plugin_data.plugin_dir / dockerfile_path_str
            template: bool = images_dict.get('template', True)
            image_def = JobTypeImageDef(
                source=source,
                dockerfile_path=dockerfile_path,
                template=template,
            )
            job_type.images.append(image_def)

    elif isinstance(job_type_value, list):  # Deprecated: list of template paths
        logger.warning('Using deprecated job type definition. Use dictionary format.')
        assert len(job_type_value), "job type data list shouldn't be empty"
        for item in job_type_value:
            assert isinstance(item, str), \
                f'Invalid dockerfile template path of a job type. Expected str, but found {type(item)}'
            image_def = JobTypeImageDef(
                source='jobtype',
                dockerfile_path=plugin_data.plugin_dir / item,
                template=True,
            )
            job_type.images.append(image_def)

    elif isinstance(job_type_value, str):  # Deprecated: one template path
        logger.warning('Using deprecated job type definition. Use dictionary format.')
        image_def = JobTypeImageDef(
            source='jobtype',
            dockerfile_path=plugin_data.plugin_dir / job_type_value,
            template=True,
        )
        job_type.images.append(image_def)

    elif isinstance(job_type_value, tuple):  # Deprecated: tuple of (base image path, template path)
        logger.warning('Using deprecated base images. Please use a single job template with a dictionary format.')
        image_def = JobTypeImageDef(
            source='jobtype',
            base_image_path=Path(job_type_value[0]),
            dockerfile_path=Path(job_type_value[1]),
            template=True,
        )
        job_type.images.append(image_def)

    else:
        raise RuntimeError(f'Invalid job type data. Expected dict, but found {type(job_type_value)}')

    assert len(job_type.images) > 0, 'list of job type images can not be empty'
    return job_type


def _validate_job_type(job_type: JobType):
    images: list[JobTypeImageDef] = job_type.images
    job_full_name: str = job_type.full_name
    assert len(images) > 0, 'Job type should have non-empty list of template images'

    for image_def in images:
        if image_def.source == 'jobtype':
            dockerfile_path = image_def.dockerfile_path
            assert dockerfile_path.is_file(), f'cannot find Dockerfile for {job_full_name} job type: {dockerfile_path}'


def list_jobtype_names_of_plugins(plugin_engine: PluginEngine) -> list[tuple[PluginManifest, str]]:
    entries: list[tuple[PluginManifest, str]] = []
    for plugin_data, result in plugin_engine.invoke_hook_with_origin(PluginCore.job_types):
        if result:
            for jobtype_name in result.keys():
                entries.append((plugin_data.plugin_manifest, jobtype_name))
    return entries
