from typing import Dict

from racetrack_client.utils.request import Requests
from fatman_wrapper.entrypoint import FatmanEntrypoint


class ForwardEntrypoint(FatmanEntrypoint):
    """Entrypoint forwarding requests to other HTTP service"""

    def __init__(self, entrypoint_hostname):
        self.entrypoint_hostname = entrypoint_hostname
        self.entrypoint_port = 7004

    def perform(self, **kwargs) -> Dict:
        response = Requests.post(
            f'http://{self.entrypoint_hostname}:{self.entrypoint_port}/perform',
            json=kwargs,
        )
        response.raise_for_status()
        return response.json()


def instantiate_host_entrypoint(entrypoint_url: str) -> FatmanEntrypoint:
    return ForwardEntrypoint(entrypoint_url)
