from typing import List, Optional, Tuple
import importlib.util
import os
import sys
from importlib.abc import Loader
from pathlib import Path
import zipfile

from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.shell import shell
from racetrack_client.utils.datamodel import parse_yaml_datamodel
from racetrack_commons.plugin.plugin_manifest import PluginData, PluginManifest
from racetrack_commons.plugin.core import PluginCore

logger = get_logger(__name__)

PLUGIN_CLASS_NAME = 'Plugin'
PLUGIN_FILENAME = 'plugin.py'
PLUGIN_MANIFEST_FILENAME = 'plugin-manifest.yaml'
EXTRACTED_PLUGINS_DIR = 'extracted'


def load_plugins_from_dir(plugins_dir: str) -> List[PluginData]:
    plugins_path = Path(plugins_dir)
    plugins_path.mkdir(parents=True, exist_ok=True)
    plugins_data: List[PluginData] = []

    for plugin_zip_path in sorted(plugins_path.glob('*.zip')):
        with wrap_context(f'extracting plugin from {plugin_zip_path.name}'):
            plugin_data = load_plugin_from_zip(plugin_zip_path)
            plugins_data.append(plugin_data)

    return sorted(plugins_data, key=lambda p: p.plugin_manifest.priority)


def load_plugin_from_zip(plugin_zip_path: Path) -> PluginData:
    assert plugin_zip_path.is_file(), f'no such file {plugin_zip_path}'
    extracted_plugin_path = plugin_zip_path.parent / EXTRACTED_PLUGINS_DIR / plugin_zip_path.stem
    
    if not extracted_plugin_path.is_dir():
        extracted_plugin_path.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(plugin_zip_path.as_posix(), 'r') as zip_ref:
            zip_ref.extractall(extracted_plugin_path)

    return load_plugin_from_dir(extracted_plugin_path, plugin_zip_path)


def load_plugin_from_dir(plugin_dir: Path, zip_path: Path) -> PluginData:
    plugin_manifest = load_plugin_manifest(plugin_dir)

    _install_plugin_dependencies(plugin_dir)
    plugin = _load_plugin_class(plugin_dir)
    setattr(plugin, 'plugin_manifest', plugin_manifest)
    setattr(plugin, 'plugin_dir', plugin_dir)
    
    logger.info(f'plugin loaded: {plugin_manifest.name} (version {plugin_manifest.version})')
    return PluginData(zip_path=zip_path, plugin_manifest=plugin_manifest, plugin_instance=plugin)


def load_plugin_manifest(plugin_dir: Path) -> PluginManifest:
    manifest_file = plugin_dir / PLUGIN_MANIFEST_FILENAME
    assert manifest_file.is_file(), f'plugin manifest file was not found in {manifest_file}'
    yaml_str = manifest_file.read_text()
    return parse_yaml_datamodel(yaml_str, PluginManifest)


def _install_plugin_dependencies(plugin_dir: Path):
    requirements = plugin_dir / 'requirements.txt'
    if requirements.is_file():
        dependencies = ', '.join(requirements.read_text().splitlines())
        logger.debug(f'installing package dependencies from {requirements}: {dependencies}')
        shell(f'pip install -r requirements.txt', workdir=plugin_dir)


def _load_plugin_class(plugin_dir: Path) -> PluginCore:
    """Load plugin class from plugin directory"""
    plugin_filename = (plugin_dir / PLUGIN_FILENAME).relative_to(plugin_dir)

    # change working directory to enable imports in plugin module
    original_cwd = os.getcwd()
    os.chdir(plugin_dir)
    sys.path.append(os.getcwd())

    try:
        spec = importlib.util.spec_from_file_location("racetrack_plugin", plugin_filename)
        ext_module = importlib.util.module_from_spec(spec)
        loader: Optional[Loader] = spec.loader
        assert loader is not None, 'no module loader'
        loader.exec_module(ext_module)

        assert hasattr(ext_module, PLUGIN_CLASS_NAME), f'class name {PLUGIN_CLASS_NAME} was not found'
        plugin_class = getattr(ext_module, PLUGIN_CLASS_NAME)
        plugin = plugin_class()

    finally:
        sys.path.remove(os.getcwd())
        os.chdir(original_cwd)

    return plugin
