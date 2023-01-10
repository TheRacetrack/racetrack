from collections import namedtuple
from typing import Optional, List

from django import template
from pydantic import BaseModel

from racetrack_client.utils.datamodel import datamodel_to_yaml_str
from racetrack_client.utils.time import timestamp_to_datetime, datetime_to_str, timestamp_pretty_ago
from racetrack_commons.entities.dto import FatmanDto

register = template.Library()

FatmanLabel = namedtuple('FatmanLabel', ['name', 'value'])


def timestamp_to_iso8601(timestamp: Optional[int]) -> Optional[str]:
    if timestamp is None:
        return None
    try:
        return datetime_to_str(timestamp_to_datetime(timestamp))
    except ValueError:
        return ''


def timestamp_to_ago_str(timestamp: Optional[int]) -> Optional[str]:
    if timestamp is None:
        return None
    try:
        return timestamp_pretty_ago(timestamp)
    except ValueError:
        return ''


def datamodel_to_yaml(dt: Optional[BaseModel]) -> str:
    if dt is None:
        return ''
    return datamodel_to_yaml_str(dt).strip()


@register.simple_tag
def fatman_labels(fatman: FatmanDto) -> List[FatmanLabel]:
    """Get fatman labels to display (metadata for humans)"""
    if not fatman.manifest:
        return []
    if not fatman.manifest.labels:
        return []
    names = sorted(fatman.manifest.labels.keys())
    return [FatmanLabel(name, fatman.manifest.labels[name]) for name in names]


register.filter(timestamp_to_iso8601)
register.filter(timestamp_to_ago_str)
register.filter(datamodel_to_yaml)
