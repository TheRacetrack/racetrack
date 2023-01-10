from typing import List, Optional
from dataclasses import dataclass

from lifecycle.auth.authorize import list_permitted_fatmen
from lifecycle.auth.subject import find_auth_subject_by_esc_id, find_auth_subject_by_fatman_family_name
from lifecycle.config.config import Config
from lifecycle.fatman.esc import list_escs
from lifecycle.fatman.registry import list_fatmen_registry
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.entities.dto import EscDto, FatmanDto
from racetrack_commons.urls import get_external_pub_url
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger
from lifecycle.django.registry import models

logger = get_logger(__name__)


@dataclass
class FatmanGraphNode:
    id: str
    type: str
    title: str
    subtitle: Optional[str] = None


@dataclass
class FatmanGraphEdge:
    from_id: str
    to_id: str


@dataclass
class FatmanGraph:
    nodes: List[FatmanGraphNode]
    edges: List[FatmanGraphEdge]


def build_fatman_dependencies_graph(config: Config, auth_subject: Optional[models.AuthSubject]) -> FatmanGraph:
    fatmen: List[FatmanDto] = list_fatmen_registry(config, auth_subject)
    family_names = _group_fatman_families(fatmen)
    escs: List[EscDto] = list(list_escs())

    nodes: List[FatmanGraphNode] = []
    for esc in escs:
        nodes.append(FatmanGraphNode(
            id=f'esc-{esc.id}',
            type='esc',
            title=f'{esc.name}',
            subtitle=f'ESC:\n{esc.id}',
        ))
    for family_name in family_names:
        fatmen_details = _list_family_fatmen_details(fatmen, family_name, config)
        nodes.append(FatmanGraphNode(
            id=f'fatman-family-{family_name}',
            type='fatman-family',
            title=f'{family_name}',
            subtitle=f'Fatman Family: {family_name}\nFatmen:\n{fatmen_details}',
        ))

    edges: List[FatmanGraphEdge] = []

    for family_name in family_names:
        try:
            auth_subject = find_auth_subject_by_fatman_family_name(family_name)
        except EntityNotFound:
            logger.warning(f'Could not find auth subject for fatman family {family_name}')
            continue
        dest_fatmen = list_permitted_fatmen(auth_subject, AuthScope.CALL_FATMAN.value, fatmen)
        dest_families = _group_fatman_families(dest_fatmen)

        for dest_family in dest_families:
            edges.append(FatmanGraphEdge(
                from_id=f'fatman-family-{family_name}',
                to_id=f'fatman-family-{dest_family}',
            ))

    for esc in escs:
        try:
            auth_subject = find_auth_subject_by_esc_id(esc.id)
        except EntityNotFound:
            logger.warning(f'Could not find auth subject for ESC {esc.id}')
            continue
        dest_fatmen = list_permitted_fatmen(auth_subject, AuthScope.CALL_FATMAN.value, fatmen)
        dest_families = _group_fatman_families(dest_fatmen)

        for dest_family in dest_families:
            edges.append(FatmanGraphEdge(
                from_id=f'esc-{esc.id}',
                to_id=f'fatman-family-{dest_family}',
            ))

    return FatmanGraph(nodes=nodes, edges=edges)


def _list_family_fatmen_details(fatmen: List[FatmanDto], family_name: str, config: Config) -> str:
    family_fatmen = [f for f in fatmen if f.name == family_name]
    return '\n'.join(('- ' + _get_fatman_details(f, config) for f in family_fatmen))


def _get_fatman_details(fatman: FatmanDto, config: Config) -> str:
    external_pub_url = get_external_pub_url(config.external_pub_url)
    url = f'{external_pub_url}/fatman/{fatman.name}/{fatman.version}'
    return f'{fatman.name} v{fatman.version} - {url}'


def _group_fatman_families(fatmen: List[FatmanDto]) -> List[str]:
    return list(set([f.name for f in fatmen]))
