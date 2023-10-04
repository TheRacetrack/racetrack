from pydantic import BaseModel

from lifecycle.deployer.base import JobDeployer
from lifecycle.monitor.base import JobMonitor, LogsStreamer


class InfrastructureTarget(BaseModel, arbitrary_types_allowed=True):
    name: str | None = None
    job_deployer: JobDeployer | None = None
    job_monitor: JobMonitor | None = None
    logs_streamer: LogsStreamer | None = None
    remote_gateway_url: str | None = None
    remote_gateway_token: str | None = None
