import io
from pathlib import Path
import zipfile
import re

from racetrack_client.log.logs import get_logger
from racetrack_client.log.context_error import wrap_context
from racetrack_client.utils.datamodel import parse_yaml_datamodel, datamodel_to_yaml_str
from racetrack_client.utils.time import now
from racetrack_commons.plugin.plugin_manifest import PluginManifest

logger = get_logger(__name__)

IGNORED_FILE_PATTERNS = [
    r'\.zip$',
    r'^\.git/',
    r'/\.git/',
    r'\.pyc$',
    r'__pycache__',
]

PLUGIN_FILENAME = 'plugin.py'
PLUGIN_MANIFEST_FILENAME = 'plugin-manifest.yaml'


def bundle_plugin(workdir: str):
    plugin_dir = Path(workdir)
    assert (plugin_dir / PLUGIN_FILENAME).is_file(), f'plugin directory should contain {PLUGIN_FILENAME} file'

    plugin_manifest_file = plugin_dir / PLUGIN_MANIFEST_FILENAME
    assert plugin_manifest_file.is_file(), f'plugin directory should contain {PLUGIN_MANIFEST_FILENAME} file'
    plugin_manifest = _load_plugin_manifest(plugin_manifest_file)

    out_path = plugin_dir / f'{plugin_manifest.name}-{plugin_manifest.version}.zip'

    ignored_patterns = [re.compile(pattern) for pattern in IGNORED_FILE_PATTERNS]

    with zipfile.ZipFile(out_path.as_posix(), mode="w", compression=zipfile.ZIP_STORED) as zip:
        for file in plugin_dir.rglob('*'):

            if file.is_dir():
                continue
            relative_path = file.relative_to(plugin_dir).as_posix()
            if any(pattern.search(relative_path) for pattern in ignored_patterns):
                continue
            if relative_path == PLUGIN_MANIFEST_FILENAME:
                continue

            logger.debug(f'writing file to zip: {relative_path}')
            zip.write(file.as_posix(), arcname=relative_path)

        _write_plugin_manifest(zip, plugin_manifest)

    logger.info(f'plugin {plugin_manifest.name} has been exported to: {out_path.absolute()}')


def _load_plugin_manifest(manifest_file: Path) -> PluginManifest:
    with wrap_context(f'parsing plugin manfiest from {manifest_file}'):
        yaml_str = manifest_file.read_text()
        return parse_yaml_datamodel(yaml_str, PluginManifest)


def _write_plugin_manifest(zip, plugin_manifest: PluginManifest):
    logger.debug(f'writing plugin manifest to zip: {PLUGIN_MANIFEST_FILENAME}')
    plugin_manifest.build_date = now().strftime('%Y-%m-%dT%H%M%SZ')
    manifest_output = io.StringIO()
    manifest_output.write(datamodel_to_yaml_str(plugin_manifest))
    zip.writestr(PLUGIN_MANIFEST_FILENAME, manifest_output.getvalue())
