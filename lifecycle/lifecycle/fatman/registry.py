from typing import Iterable, Dict, Optional, List
from collections import defaultdict
from lifecycle.auth.authorize import list_permitted_families, list_permitted_fatmen

from lifecycle.config import Config
from lifecycle.deployer.deployers import get_fatman_deployer
from lifecycle.fatman import models_registry
from lifecycle.fatman.audit import AuditLogger
from lifecycle.fatman.dto_converter import fatman_model_to_dto, fatman_family_model_to_dto
from lifecycle.monitor.monitors import list_cluster_fatmen
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.deploy.resource import fatman_resource_name
from racetrack_commons.entities.audit import AuditLogEventType
from racetrack_commons.entities.dto import FatmanDto, FatmanFamilyDto, FatmanStatus
from lifecycle.django.registry import models
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine

logger = get_logger(__name__)


def list_fatmen_registry(config: Config, auth_subject: Optional[models.AuthSubject] = None) -> List[FatmanDto]:
    """List fatmen getting results from registry (Database)"""
    if auth_subject is None:
        return [fatman_model_to_dto(fatman, config) for fatman in models_registry.list_fatmen_models()]
    else:
        fatmen = [fatman_model_to_dto(fatman, config) for fatman in models_registry.list_fatmen_models()]
        return list_permitted_fatmen(auth_subject, AuthScope.READ_FATMAN.value, fatmen)


def list_fatman_families(auth_subject: Optional[models.AuthSubject] = None) -> Iterable[FatmanFamilyDto]:
    """List fatmen getting results from registry (Database)"""
    if auth_subject is None:
        return [fatman_family_model_to_dto(family) for family in models_registry.list_fatman_family_models()]
    else:
        families = [fatman_family_model_to_dto(family) for family in models_registry.list_fatman_family_models()]
        return list_permitted_families(auth_subject, AuthScope.READ_FATMAN.value, families)


def read_fatman_family(fatman_family: str) -> FatmanFamilyDto:
    """Read fatmen family from registry (Database)"""
    family_model = models_registry.read_fatman_family_model(fatman_family)
    return fatman_family_model_to_dto(family_model)


def read_fatman(fatman_name: str, fatman_version: str, config: Config) -> FatmanDto:
    """
    Find deployed fatman by name and version
    :param fatman_name: name of the fatman
    :param fatman_version: fatman version name
    :param config: Lifecycle configuration
    :return: deployed fatman as data model
    :raise EntityNotFound if fatman with given name doesn't exist
    """
    fatman_model = models_registry.read_fatman_model(fatman_name, fatman_version)
    return fatman_model_to_dto(fatman_model, config)


def read_versioned_fatman(fatman_name: str, fatman_version: str, config: Config) -> FatmanDto:
    """Find fatman by name and version, accepting version aliases"""
    fatman_model = models_registry.resolve_fatman_model(fatman_name, fatman_version)
    return fatman_model_to_dto(fatman_model, config)


def delete_fatman(
    fatman_name: str,
    fatman_version: str,
    config: Config,
    username: str,
    plugin_engine: PluginEngine,
):
    fatman = read_fatman(fatman_name, fatman_version, config)  # raise 404 if not found
    if fatman.status != FatmanStatus.LOST.value:
        get_fatman_deployer(config, plugin_engine).delete_fatman(fatman_name, fatman_version)

    owner_username = fatman.deployed_by
    AuditLogger().log_event(
        AuditLogEventType.FATMAN_DELETED,
        username_executor=username,
        username_subject=owner_username,
        fatman_name=fatman.name,
        fatman_version=fatman.version,
    )

    models_registry.create_trashed_fatman(fatman)
    models_registry.delete_fatman_model(fatman_name, fatman_version)

    plugin_engine.invoke_plugin_hook(PluginCore.post_fatman_delete, fatman, username_executor=username)


def sync_registry_fatmen(config: Config, plugin_engine: PluginEngine):
    """Synchronize fatman stored in registry and confront it with Kubernetes source of truth"""
    logger.info("Synchronizing fatmen")

    with wrap_context('synchronizing fatman'):
        cluster_fatmen = _generate_fatmen_map(list_cluster_fatmen(config, plugin_engine))
        registry_fatmen = _generate_fatmen_map(list_fatmen_registry(config))
        logger.debug(f'Found {len(cluster_fatmen)} fatmen in the cluster, {len(registry_fatmen)} in the database')
        fatmen_status_count: Dict[str, int] = defaultdict(int)

        for fatman_id, registry_fatman in registry_fatmen.items():
            if fatman_id in cluster_fatmen:
                cluster_fatman = cluster_fatmen[fatman_id]
                _sync_registry_fatman(registry_fatman, cluster_fatman)
            else:
                # fatman not present in Cluster
                if registry_fatman.status != FatmanStatus.LOST.value:
                    logger.info(f'fatman is lost: {registry_fatman}')
                    registry_fatman.status = FatmanStatus.LOST.value
                    models_registry.save_fatman_model(registry_fatman)

            fatmen_status_count[registry_fatman.status] += 1

        # Orphans - fatman missing in registry but present in cluster
        for fatman_id, cluster_fatman in cluster_fatmen.items():
            if fatman_id not in registry_fatmen:
                logger.info(f'orphaned fatman found: {cluster_fatman}')
                cluster_fatman.status = FatmanStatus.ORPHANED.value
                models_registry.save_fatman_model(cluster_fatman)
                fatmen_status_count[cluster_fatman.status] += 1

        logger.debug(f'Fatmen synchronized, count by status: {dict(fatmen_status_count)}')


def _sync_registry_fatman(registry_fatman: FatmanDto, cluster_fatman: FatmanDto):
    """
    Update database fatman with data taken from cluster.
    Do database "update" only when change is detected in order to avoid redundant database operations.
    """
    changed = False

    if registry_fatman.status != cluster_fatman.status:
        registry_fatman.status = cluster_fatman.status
        changed = True
        logger.debug(f'fatman {registry_fatman} changed status to: {registry_fatman.status}')
    if registry_fatman.error != cluster_fatman.error:
        registry_fatman.error = cluster_fatman.error
        changed = True
    if cluster_fatman.last_call_time is not None:
        if registry_fatman.last_call_time is None or registry_fatman.last_call_time < cluster_fatman.last_call_time:
            registry_fatman.last_call_time = cluster_fatman.last_call_time
            changed = True

    if changed:
        models_registry.save_fatman_model(registry_fatman)


def _generate_fatmen_map(fatmen: Iterable[FatmanDto]) -> Dict[str, FatmanDto]:
    return {fatman_resource_name(fatman.name, fatman.version): fatman for fatman in fatmen}
