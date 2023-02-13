import importlib.util
from importlib.abc import Loader
import os
from pathlib import Path
import random
import sys
from typing import List, Optional
import zipfile

from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_client.utils.semver import SemanticVersion
from racetrack_client.utils.shell import shell
from racetrack_client.utils.datamodel import parse_yaml_datamodel
from racetrack_commons.plugin.plugin_data import PluginData
from racetrack_commons.plugin.core import PluginCore

logger = get_logger(__name__)

PLUGIN_CLASS_NAME = 'Plugin'
PLUGIN_FILENAME = 'plugin.py'
PLUGIN_MANIFEST_FILENAME = 'plugin-manifest.yaml'
EXTRACTED_PLUGINS_DIR = 'extracted'
PLUGINS_CONFIG_DIR = 'config'
PLUGIN_CONFIG_FILENAME = 'config.yaml'


def load_plugins_from_dir(plugins_dir: str) -> List[PluginData]:
    """
    Loads Racetrack plugins from a directory containing the ZIP files.
    Loaded plugins will be sorted by priority, then by plugin version ascending.
    """
    plugins_path = Path(plugins_dir)
    ensure_dir_exists(plugins_path)

    plugins_data: List[PluginData] = []

    for plugin_zip_path in sorted(plugins_path.glob('*.zip')):
        plugin_data = load_plugin_from_zip(plugin_zip_path)
        plugins_data.append(plugin_data)

    plugins_data.sort(key=lambda p: (p.plugin_manifest.priority, SemanticVersion(p.plugin_manifest.version)))
    return plugins_data


def load_plugin_from_zip(plugin_zip_path: Path) -> PluginData:
    with wrap_context(f'loading plugin from {plugin_zip_path.name}'):
        assert plugin_zip_path.is_file(), f'no such file {plugin_zip_path}'
        
        extracted_plugins_dir = plugin_zip_path.parent / EXTRACTED_PLUGINS_DIR
        ensure_dir_exists(extracted_plugins_dir)
        extracted_plugin_path = extracted_plugins_dir / plugin_zip_path.stem

        plugins_config_dir = plugin_zip_path.parent / PLUGINS_CONFIG_DIR
        ensure_dir_exists(plugins_config_dir)
        ensure_dir_exists(plugins_config_dir / plugin_zip_path.stem)
        config_file = plugins_config_dir / plugin_zip_path.stem / PLUGIN_CONFIG_FILENAME
        if not config_file.is_file():
            config_file.touch()
            try:
                config_file.chmod(mode=0o666)
            except PermissionError:
                logger.warning(f'Can\'t change permissions of {config_file}')
        
        init_dir = False
        if not extracted_plugin_path.is_dir():
            extracted_plugin_path.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(plugin_zip_path.as_posix(), 'r') as zip_ref:
                zip_ref.extractall(extracted_plugin_path)
            init_dir = True

        return load_plugin_from_dir(extracted_plugin_path, config_file, plugin_zip_path, init_dir)


def load_plugin_from_dir(plugin_dir: Path, config_path: Path, zip_path: Path, init_dir: bool) -> PluginData:
    plugin_manifest = load_plugin_manifest(plugin_dir)

    _install_plugin_dependencies(plugin_dir)
    plugin = _load_plugin_class(plugin_dir, config_path, plugin_manifest)
    setattr(plugin, 'plugin_manifest', plugin_manifest)
    setattr(plugin, 'plugin_dir', plugin_dir)
    setattr(plugin, 'config_path', config_path)

    if init_dir:  # set permissions after loading a class due to *.pyc created after all
        try:
            plugin_dir.chmod(mode=0o777)
            for p in plugin_dir.rglob("*"):
                if p.is_dir():
                    p.chmod(mode=0o777)
                else:
                    p.chmod(mode=0o666)
        except PermissionError:
            logger.warning(f'Can\'t change permissions in {plugin_dir}')
    
    logger.debug(f'plugin loaded: {plugin_manifest.name} (version {plugin_manifest.version})')
    return PluginData(zip_path=zip_path, config_path=config_path, plugin_manifest=plugin_manifest, plugin_instance=plugin)


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
        shell(f'python -m pip install --user -r requirements.txt', workdir=plugin_dir)


def _load_plugin_class(plugin_dir: Path, config_path: Path, plugin_manifest: PluginManifest) -> PluginCore:
    """Load plugin class from plugin directory"""
    plugin_filename = (plugin_dir / PLUGIN_FILENAME).relative_to(plugin_dir)

    # change working directory to enable imports in plugin module
    plugin_dir_posix = plugin_dir.absolute().resolve().as_posix()
    original_cwd = os.getcwd()
    os.chdir(plugin_dir_posix)
    sys.path.append(plugin_dir_posix)

    core_modules = set(sys.modules.keys())

    try:
        with wrap_context(f'loading plugin class'):
            module_name = f'racetrack_plugin_{random.randint(0, 999999)}'
            spec = importlib.util.spec_from_file_location(module_name, plugin_filename)
            ext_module = importlib.util.module_from_spec(spec)
            loader: Optional[Loader] = spec.loader
            assert loader is not None, 'no module loader'
            loader.exec_module(ext_module)

            assert hasattr(ext_module, PLUGIN_CLASS_NAME), f'class name {PLUGIN_CLASS_NAME} was not found'
            plugin_class = getattr(ext_module, PLUGIN_CLASS_NAME)

        setattr(plugin_class, 'plugin_manifest', plugin_manifest)
        setattr(plugin_class, 'plugin_dir', plugin_dir)
        setattr(plugin_class, 'config_path', config_path)

        with wrap_context(f'instantiating plugin class'):
            plugin = plugin_class()

    finally:
        sys.path.remove(plugin_dir_posix)
        os.chdir(original_cwd)
        # Unload the cached plugin's modules to prevent from using them by other plugins
        plugin_modules = set(sys.modules.keys()) - core_modules
        if plugin_modules:
            for mod in plugin_modules:
                del sys.modules[mod]

    return plugin


def ensure_dir_exists(path: Path):
    if not path.is_dir():
        path.mkdir(parents=True, exist_ok=True)
        try:
            path.chmod(mode=0o777)
        except PermissionError:
            logger.warning(f'Can\'t change permissions of {path}')
