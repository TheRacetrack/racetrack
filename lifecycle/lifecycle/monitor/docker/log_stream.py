from typing import Dict

from lifecycle.monitor.base import LogsStreamer
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.shell import CommandOutputStream, CommandError
from racetrack_commons.deploy.resource import fatman_resource_name

logger = get_logger(__name__)


class DockerLogsStreamer(LogsStreamer):
    """Source of a Fatman logs retrieved from a Docker container"""

    def __init__(self):
        super().__init__()
        self.sessions: Dict[str, CommandOutputStream] = {}

    def create_session(self, session_id: str, resource_properties: Dict[str, str]):
        """Start a session transmitting messages to a client."""
        fatman_name = resource_properties.get('fatman_name')
        fatman_version = resource_properties.get('fatman_version')
        tail = resource_properties.get('tail')
        container_name = fatman_resource_name(fatman_name, fatman_version)

        def on_next_line(line: str):
            self.broadcast(session_id, line)

        def on_error(error: CommandError):
            # Negative return value is the signal number which was used to kill the process. SIGTERM is 15.
            if error.returncode != -15:  # ignore process Terminated on purpose
                logger.error(f'command "{error.cmd}" failed with return code {error.returncode}')

        cmd = f'docker logs "{container_name}" --follow --tail {tail}'
        output_stream = CommandOutputStream(cmd, on_next_line=on_next_line, on_error=on_error)
        self.sessions[session_id] = output_stream

    def close_session(self, session_id: str):
        output_stream = self.sessions[session_id]
        output_stream.interrupt()
        del self.sessions[session_id]
