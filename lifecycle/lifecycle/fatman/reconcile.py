from lifecycle.config import Config
from lifecycle.deployer.redeploy import reprovision_fatman
from lifecycle.fatman.registry import list_job_registry
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_client.log.context_error import wrap_context, ContextError
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import FatmanDto, FatmanStatus

logger = get_logger(__name__)


def reconcile_fatmen(config: Config, plugin_engine: PluginEngine):
    """Redeploy fatmen missing in a cluster"""
    with wrap_context('reconciling fatmen'):
        for fatman in list_job_registry(config):
            try:
                if is_fatman_reconcile_eligible(fatman):
                    logger.info(f'reconciling lost fatman {fatman}...')
                    reprovision_fatman(fatman.name, fatman.version, config, plugin_engine, 'racetrack', None)

            except BaseException as e:
                log_exception(ContextError('failed to reconcile fatman', e))


def is_fatman_reconcile_eligible(fatman: FatmanDto) -> bool:
    if fatman.status != FatmanStatus.LOST.value:
        return False
    if fatman.manifest is None:
        return False
    return True
