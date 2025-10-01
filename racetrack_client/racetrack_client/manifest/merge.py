from pathlib import Path
from typing import Dict, List

import yaml

from racetrack_client.log.context_error import wrap_context
from racetrack_client.manifest import Manifest
from racetrack_client.manifest.load import load_manifest_dict_from_yaml, load_manifest_from_dict


def load_merged_manifest(manifest_path: Path, extra_vars: Dict[str, str]) -> Manifest:
    """Load manifest from YAML file, resolve overlay layer, merging it with base manifest"""
    manifest_dict = load_merged_manifest_dict(manifest_path, extra_vars)
    return load_manifest_from_dict(manifest_dict)


def load_merged_manifest_dict(manifest_path: Path, extra_vars: Dict[str, str]) -> Dict:
    """
    Load dictionary representation of a manifest from YAML file, resolve overlay layer, merging it with base manifest
    """
    with wrap_context('loading manifest'):
        manifest_dict = load_manifest_dict_from_yaml(manifest_path)

    extends = manifest_dict.get('extends')
    if extends:
        extends_path = Path(extends)
        with wrap_context('extending base manifest with overlay'):
            with wrap_context('loading base manifest'):
                assert not extends_path.is_absolute(), 'extends path should be relative'
                base_path = manifest_path.parent / extends_path
                base_manifest_dict = load_manifest_dict_from_yaml(base_path)
                assert not base_manifest_dict.get('extends'), 'base manifest cannot extend another one'
            with wrap_context('merging base & overlay layers'):
                manifest_dict = merge_dicts(base_manifest_dict, manifest_dict)
                manifest_dict['extends'] = None

    if extra_vars:
        with wrap_context('applying extra vars'):
            for extra_key, extra_value in extra_vars.items():
                assert extra_key, 'extra var key cannot be empty'
                key_nodes: List[str] = extra_key.split('.')
                last_name = key_nodes[-1]
                target_node: Dict = manifest_dict
                for key_node in key_nodes[:-1]:
                    target_node = target_node[key_node]
                value_object = yaml.safe_load(extra_value)
                target_node[last_name] = value_object

    return manifest_dict


def merge_dicts(base: Dict, overlay: Dict) -> Dict:
    """
    Merge dict overlay into base recursively (in case of same keys).
    Entries from overlay will overwrite entries from base.
    """
    for key in overlay:
        if key in base:
            if isinstance(base[key], dict) and isinstance(overlay[key], dict):
                base[key] = merge_dicts(base[key], overlay[key])
            else:
                base[key] = overlay[key]
        else:
            base[key] = overlay[key]
    return base
