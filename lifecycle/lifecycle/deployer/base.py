from abc import ABC, abstractmethod
from typing import Dict

from lifecycle.config import Config
from lifecycle.deployer.secrets import FatmanSecrets
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_client.manifest import Manifest
from racetrack_commons.entities.dto import FatmanDto, FatmanFamilyDto


class FatmanDeployer(ABC):
    @abstractmethod
    def deploy_fatman(
        self,
        manifest: Manifest,
        config: Config,
        plugin_engine: PluginEngine,
        tag: str,
        runtime_env_vars: Dict[str, str],
        family: FatmanFamilyDto,
    ) -> FatmanDto:
        """Deploy a Fatman from a manifest file"""
        raise NotImplementedError()

    @abstractmethod
    def delete_fatman(self, fatman_name: str, fatman_version: str):
        """Delete a fatman based on its name"""
        raise NotImplementedError()

    @abstractmethod
    def fatman_exists(self, fatman_name: str, fatman_version: str) -> bool:
        """Tell whether a fatman already exists or not"""
        raise NotImplementedError()

    @abstractmethod
    def save_fatman_secrets(
        self,
        fatman_name: str,
        fatman_version: str,
        fatman_secrets: FatmanSecrets,
    ):
        """Create or update secrets needed to build and deploy a fatman"""
        raise NotImplementedError()

    @abstractmethod
    def get_fatman_secrets(
        self,
        fatman_name: str,
        fatman_version: str,
    ) -> FatmanSecrets:
        """Retrieve secrets for building and deploying a fatman"""
        raise NotImplementedError()
