from abc import ABC, abstractmethod
from typing import Dict

from lifecycle.config import Config
from lifecycle.deployer.secrets import JobSecrets
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_client.manifest import Manifest
from racetrack_commons.entities.dto import JobDto, JobFamilyDto


class JobDeployer(ABC):
    @abstractmethod
    def deploy_job(
        self,
        manifest: Manifest,
        config: Config,
        plugin_engine: PluginEngine,
        tag: str,
        runtime_env_vars: Dict[str, str],
        family: JobFamilyDto,
        containers_num: int = 1,
        runtime_secret_vars: Dict[str, str] | None = None,
    ) -> JobDto:
        """Deploy a Job from a manifest file"""
        raise NotImplementedError()

    @abstractmethod
    def delete_job(self, job_name: str, job_version: str):
        """Delete a Job based on its name"""
        raise NotImplementedError()

    @abstractmethod
    def job_exists(self, job_name: str, job_version: str) -> bool:
        """Tell whether a Job already exists or not"""
        raise NotImplementedError()

    @abstractmethod
    def save_job_secrets(
        self,
        job_name: str,
        job_version: str,
        job_secrets: JobSecrets,
    ):
        """Create or update secrets needed to build and deploy a Job"""
        raise NotImplementedError()

    @abstractmethod
    def get_job_secrets(
        self,
        job_name: str,
        job_version: str,
    ) -> JobSecrets:
        """Retrieve secrets for building and deploying a Job"""
        raise NotImplementedError()
