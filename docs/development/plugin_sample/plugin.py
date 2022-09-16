from typing import Dict, Optional
import logging

from racetrack_client.manifest import Manifest
from racetrack_commons.entities.dto import FatmanDto


class Plugin:
    def post_fatman_deploy(self, manifest: Manifest, fatman: FatmanDto, image_name: str, deployer_username: str = None):
        if 'skynet' in manifest.name:
            logging.warning(f'ATTENTION: Skynet is armed again!')

    def fatman_runtime_env_vars(self) -> Optional[Dict[str, str]]:
        return {
            'SKYNET_TARGET': "MrPresident",
        }
