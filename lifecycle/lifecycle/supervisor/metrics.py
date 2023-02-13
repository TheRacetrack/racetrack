from pathlib import Path

from lifecycle.config import Config
from lifecycle.fatman.registry import list_fatmen_registry
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import FatmanDto, FatmanStatus
from racetrack_commons.plugin.loader import ensure_dir_exists

logger = get_logger(__name__)


def populate_metrics_jobs(config: Config):
    """
    Populate a configuration file for Prometheus to discover all the jobs
    using `file_sd_configs` feature
    """
    metrics_dir = Path(config.plugins_dir) / 'metrics'
    ensure_dir_exists(metrics_dir)
    service_discovery_file: Path = metrics_dir / 'sd_config_jobs.yaml'

    file_content: list[str] = []
    with wrap_context('populating Prometheus configuration'):
        for job in list_fatmen_registry(config):
            if job.status != FatmanStatus.LOST.value:
                file_content.append(_build_job_config(job))

    service_discovery_file.write_text('\n'.join(file_content))


def _build_job_config(job: FatmanDto) -> str:
    return f"""
- targets:
    - '{job.internal_name}'
  labels:
    job: 'job-{job.name}-v-{job.version}'
    job_name: '{job.name}'
    job_version: '{job.version}'
    """.strip()
