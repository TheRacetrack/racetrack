from __future__ import annotations
from abc import ABC
from typing import Any

from racetrack_client.manifest import Manifest
from racetrack_commons.entities.dto import JobDto


class PluginCore(ABC):
    """
    Abstract Racetrack Plugin with method interfaces to override

    Additional attributes can be used:
    - self.plugin_dir: pathlib.Path - path to a plugin directory
    - self.plugin_manifest: racetrack_client.plugin.plugin_manifest.PluginManifest - Details of the contents of the plugin
    - self.config_path: pathlib.Path - path to a file with plugin's config
    """

    def post_job_deploy(
        self,
        manifest: Manifest,
        job: JobDto,
        image_name: str,
        deployer_username: str | None = None,
    ):
        """
        Supplementary actions invoked after job is deployed
        :param manifest: job's manifest
        :param job: job's metadata
        :param image_name: full name of the job image
        :param deployer_username: username of the user who deployed the job
        """
        pass

    def job_runtime_env_vars(self) -> dict[str, str] | None:
        """Supplementary env vars dictionary added to runtime vars when deploying a Job"""
        return None

    def job_types(self) -> dict[str, dict]:
        """
        Job types provided by this plugin
        :return dict of job type name (with version) mapped to a definition of images to build
        """
        return {}

    def infrastructure_targets(self) -> dict[str, Any]:
        """
        Infrastructure Targets (deployment targets for Jobs) provided by this plugin
        Infrastructure Target should contain Job Deployer, Job Monitor and Job Logs Streamer.
        :return dict of infrastructure name -> an instance of lifecycle.infrastructure.model.InfrastructureTarget
        """
        return {}

    def markdown_docs(self) -> str | None:
        """
        Return documentation for this plugin in Markdown format
        """
        return None

    def run_action(self, **kwargs) -> Any:
        """Call a supplementary action of a plugin"""
        return None

    def post_job_delete(self, job: JobDto, username_executor: str | None = None):
        """
        Supplementary actions invoked after job is deleted
        :param job: job's metadata
        :param username_executor: username of the user who deleted the job
        """
        pass

    def validate_job_manifest(self, manifest: Manifest, job_type: str):
        """
        Validate job's manifest in terms of job type specific parts.
        :param manifest: job's manifest
        :param job_type: job type name with the version
        :raise Exception in case of validation error
        """
        pass
