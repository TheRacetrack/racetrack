from __future__ import annotations
from abc import ABC
from typing import Any
from pathlib import Path

from racetrack_client.manifest import Manifest
from racetrack_commons.entities.dto import FatmanDto


class PluginCore(ABC):
    """
    Abstract Racetrack Plugin with method interfaces to override

    Additional attributes can be used:
    - self.plugin_dir: pathlib.Path - path to a plugin directory
    - self.plugin_manifest: racetrack_client.plugin.plugin_manifest.PluginManifest - Details of the contents of the plugin
    - self.config_path: pathlib.Path - path to a file with plugin's config
    """

    def post_fatman_deploy(
        self,
        manifest: Manifest,
        fatman: FatmanDto,
        image_name: str,
        deployer_username: str | None = None,
    ):
        """
        Supplementary actions invoked after fatman is deployed
        :param image_name: full name of the fatman image
        :param deployer_username: username of the user who deployed the fatman
        """
        pass

    def fatman_runtime_env_vars(self) -> dict[str, str] | None:
        """Supplementary env vars dictionary added to runtime vars when deploying a Fatman"""
        return None

    def fatman_job_types(self) -> dict[str, list[tuple[Path, Path]]]:
        """
        Job types provided by this plugin
        :return dict of job type name (with version) -> list of images: (base image path, dockerfile template path)
        """
        return {}

    def infrastructure_targets(self) -> dict[str, Any]:
        """
        Infrastructure Targets (deployment targets for Fatmen) provided by this plugin
        Infrastructure Target should contain Fatman Deployer, Fatman Monitor and Fatman Logs Streamer.
        :return dict of infrastructure name -> an instance of lifecycle.deployer.infra_target.InfrastructureTarget
        """
        return {}

    def markdown_docs(self) -> str | None:
        """
        Return documentation for this plugin in markdown format
        """
        return None

    def post_fatman_delete(self, fatman: FatmanDto, username_executor: str | None = None):
        """
        Supplementary actions invoked after fatman is deleted
        :param username_executor: username of the user who deleted the fatman
        """
        pass
