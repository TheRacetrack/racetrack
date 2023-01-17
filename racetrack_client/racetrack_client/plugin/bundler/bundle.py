import io
from pathlib import Path
from typing import Optional
import zipfile

from racetrack_client.log.logs import get_logger
from racetrack_client.log.context_error import wrap_context
from racetrack_client.plugin.bundler.filename_matcher import FilenameMatcher
from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_client.utils.datamodel import parse_yaml_datamodel, datamodel_to_yaml_str
from racetrack_client.utils.time import now

logger = get_logger(__name__)

PLUGIN_FILENAME = 'plugin.py'
PLUGIN_MANIFEST_FILENAME = 'plugin-manifest.yaml'


def bundle_plugin(workdir: str, out_dir: Optional[str], plugin_version: Optional[str]):
    """Turn local plugin code into ZIP file"""
    plugin_dir = Path(workdir)
    assert (plugin_dir / PLUGIN_FILENAME).is_file(), f'{plugin_dir / PLUGIN_FILENAME} file was not found in a plugin directory'

    plugin_manifest_file = plugin_dir / PLUGIN_MANIFEST_FILENAME
    assert plugin_manifest_file.is_file(), f'{plugin_manifest_file} file was not found in a plugin directory'
    plugin_manifest = _load_plugin_manifest(plugin_manifest_file)

    if plugin_version:
        plugin_manifest.version = plugin_version

    out_dir_path = Path(out_dir) if out_dir else plugin_dir
    assert out_dir_path.is_dir(), f'out directory {out_dir_path} doesn\'t exist'
    out_path = out_dir_path / f'{plugin_manifest.name}-{plugin_manifest.version}.zip'

    ignore_file = plugin_dir / '.racetrackignore'
    if ignore_file.is_file():
        logger.info(f'ignoring file patterns found in {ignore_file}')
        inclusion_matcher = FilenameMatcher(ignore_file.read_text().splitlines())
    else:
        inclusion_matcher = FilenameMatcher()

    with zipfile.ZipFile(out_path.as_posix(), mode="w", compression=zipfile.ZIP_STORED) as zip:
        for file in plugin_dir.rglob('*'):

            if file.is_dir():
                continue
            relative_path = file.relative_to(plugin_dir)
            if not inclusion_matcher.match_path(relative_path):
                continue

            logger.debug(f'writing file to zip: {relative_path}')
            zip.write(file.as_posix(), arcname=relative_path.as_posix())

        _write_plugin_manifest(zip, plugin_manifest)

    logger.info(f'plugin {plugin_manifest.name} has been exported to: {out_path.resolve().absolute()}')


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
