from pathlib import Path
from typing import Dict

from racetrack_client.log.context_error import wrap_context
from racetrack_client.manifest import Manifest
from racetrack_client.manifest.load import load_manifest_dict_from_yaml, load_manifest_from_dict


def load_merged_manifest(manifest_path: Path) -> Manifest:
    """Load manifest from YAML file, resolve overlay layer, merging it with base manifest"""
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

    return load_manifest_from_dict(manifest_dict)


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
