from __future__ import annotations
from abc import ABC
from typing import Any
from pathlib import Path

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
        :param image_name: full name of the job image
        :param deployer_username: username of the user who deployed the job
        """
        pass

    def job_runtime_env_vars(self) -> dict[str, str] | None:
        """Supplementary env vars dictionary added to runtime vars when deploying a Job"""
        return None

    def job_types(self) -> dict[str, list[tuple[Path, Path]]]:
        """
        Job types provided by this plugin
        :return dict of job type name (with version) -> list of images: (base image path, dockerfile template path)
        """
        return {}

    def infrastructure_targets(self) -> dict[str, Any]:
        """
        Infrastructure Targets (deployment targets for Jobs) provided by this plugin
        Infrastructure Target should contain Job Deployer, Job Monitor and Job Logs Streamer.
        :return dict of infrastructure name -> an instance of lifecycle.deployer.infra_target.InfrastructureTarget
        """
        return {}

    def markdown_docs(self) -> str | None:
        """
        Return documentation for this plugin in markdown format
        """
        return None

    def run_action(self, **kwargs) -> Any:
        """Call a supplementary action of a plugin"""
        return None

    def post_job_delete(self, job: JobDto, username_executor: str | None = None):
        """
        Supplementary actions invoked after job is deleted
        :param username_executor: username of the user who deleted the job
        """
        pass
