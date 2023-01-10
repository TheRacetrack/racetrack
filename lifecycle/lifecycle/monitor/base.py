from abc import ABC, abstractmethod
from typing import Iterable, Callable, Dict

from lifecycle.config import Config
from racetrack_commons.entities.dto import FatmanDto


class FatmanMonitor(ABC):
    """Responsible for discovering workloads running in a cluster and monitoring their condition"""

    @abstractmethod
    def list_fatmen(self, config: Config) -> Iterable[FatmanDto]:
        """List fatmans deployed in a cluster"""
        raise NotImplementedError()

    @abstractmethod
    def check_fatman_condition(self,
                               fatman: FatmanDto,
                               deployment_timestamp: int = 0,
                               on_fatman_alive: Callable = None,
                               logs_on_error: bool = True,
                               ):
        """
        Verify if deployed Fatman is really operational. If not, raise exception with reason
        :param fatman: fatman data
        :param deployment_timestamp: timestamp of deployment to verify if the running version is really the expected one
        If set to zero, checking version is skipped.
        :param on_fatman_alive: handler called when Fatman is live, but not ready yet
        (server running already, but still initializing)
        :param logs_on_error: if True, logs are read from the Fatman and returned in the exception in case of failure
        """
        raise NotImplementedError()

    @abstractmethod
    def read_recent_logs(self, fatman: FatmanDto, tail: int = 20) -> str:
        """
        Return last output logs from a Fatman
        :param fatman: fatman data
        :param tail: number of recent lines to show
        :return logs output lines joined in a one string
        """
        raise NotImplementedError()


class LogsStreamer(ABC):
    """Producer of logs, setting up & tearing down sessions providing log lines stream"""

    def __init__(self):
        # callback for sending messages to connected clients
        self.broadcaster: Callable[[str, str], None] = lambda session_id, message: None

    @abstractmethod
    def create_session(self, session_id: str, resource_properties: Dict[str, str]):
        """
        Start a session transmitting messages to client.
        Session should call `broadcast` method when next message arrives.
        :param session_id: ID of a client session to be referred when closing
        :param resource_properties: properties describing a resource to be monitored (fatman name, version, etc)
        """
        pass

    def close_session(self, session_id: str):
        """Close session when a client disconnects"""
        pass

    def broadcast(self, session_id: str, message: str):
        """Send message to subscribed clients"""
        self.broadcaster(session_id, message)
