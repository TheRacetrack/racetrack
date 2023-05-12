import re
from jsonschema import validate
import json

from racetrack_client.log.context_error import wrap_context
from racetrack_client.manifest import Manifest
from racetrack_client.manifest.load import get_manifest_path
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest.merge import load_merged_manifest
from racetrack_client.utils.datamodel import datamodel_to_yaml_str
from racetrack_client.utils.semver import SemanticVersion

logger = get_logger(__name__)


def load_validated_manifest(path: str) -> Manifest:
    """
    Load and validate manifest from a path. Raise exception in case of a defect.
    :param path path to a Job manifest file or to a directory with it
    :return loaded, valid Manifest
    """
    manifest_path = get_manifest_path(path)
    manifest = load_merged_manifest(manifest_path)

    with wrap_context('validating manifest'):
        validate_manifest(manifest)

    logger.debug(f'Manifest file "{manifest_path}" is valid')
    return manifest


def validate_manifest(manifest: Manifest):
    """Check whether manifest is valid. Raise exception in case of error"""
    with open('racetrack_client/racetrack_client/manifest/schema.json', 'r') as f:
        schema = json.load(f)
        validate(manifest, schema=schema)

def validate_and_show_manifest(path: str):
    manifest = load_validated_manifest(path)
    logger.info(f'Manifest file "{path}" is valid')
    print(datamodel_to_yaml_str(manifest))
