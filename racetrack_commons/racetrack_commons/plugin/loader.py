import shutil
from typing import Optional
import importlib.util
import os
import sys
from importlib.abc import Loader
from pathlib import Path

from git import Repo

from racetrack_client.utils.shell import shell, CommandError
from racetrack_commons.plugin.plugin_config import PluginConfig
from racetrack_commons.plugin.core import PluginCore
from racetrack_client.log.context_error import ContextError, wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_commons.dir import project_root


logger = get_logger(__name__)

PLUGIN_CLASS_NAME = 'Plugin'
PLUGIN_FILENAME = 'plugin.py'


def load_plugin(plugin_config: PluginConfig) -> PluginCore:
    logger.debug(f'loading plugin: {plugin_config.name}')
    plugin_dir = _download_plugin(plugin_config)
    _install_plugin_dependencies(plugin_dir)
    plugin = _load_plugin_class(plugin_dir)
    setattr(plugin, 'plugin_config', plugin_config)
    
    logger.info(f'loaded plugin: {plugin_config.name} (version {plugin_config.git_ref})')
    return plugin


def _download_plugin(plugin_config: PluginConfig) -> Path:
    """Download plugin to local plugins directory"""
    plugins_path = project_root() / '.plugins'
    plugins_path.mkdir(parents=True, exist_ok=True)
    assert plugins_path.is_dir(), 'plugins directory doesn\'t exist'
    plugin_path = plugins_path / plugin_config.name
    plugin_dir = _fetch_plugin_repo(plugin_path, plugin_config)
    return plugin_dir


def _install_plugin_dependencies(plugin_dir: Path):
    requirements = plugin_dir / 'requirements.txt'
    if requirements.is_file():
        shell(f'pip install -r requirements.txt', workdir=plugin_dir)


def _load_plugin_class(plugin_dir: Path) -> PluginCore:
    """Load plugin class from plugin directory"""
    plugin_filename = (plugin_dir / PLUGIN_FILENAME).relative_to(plugin_dir)

    # change working directory to enable imports in plugin module
    original_cwd = os.getcwd()
    os.chdir(plugin_dir)
    sys.path.append(os.getcwd())

    spec = importlib.util.spec_from_file_location("racetrack_plugin", plugin_filename)
    ext_module = importlib.util.module_from_spec(spec)
    loader: Optional[Loader] = spec.loader
    assert loader is not None, 'no module loader'
    loader.exec_module(ext_module)

    assert hasattr(ext_module, PLUGIN_CLASS_NAME), f'class name {PLUGIN_CLASS_NAME} was not found'
    plugin_class = getattr(ext_module, PLUGIN_CLASS_NAME)
    plugin = plugin_class()
    plugin.plugin_dir = plugin_dir

    sys.path.remove(os.getcwd())
    os.chdir(original_cwd)

    return plugin


def _fetch_plugin_repo(plugin_path: Path, plugin_config: PluginConfig) -> Path:
    """Clone git repository to local plugin directory"""
    remote_url = plugin_config.git_remote

    if plugin_path.is_dir():
        shutil.rmtree(plugin_path)

    with wrap_context('cloning git repo'):
        try:
            shell(f'GIT_TERMINAL_PROMPT=0 git clone {remote_url} {plugin_path.resolve()}', 
                  workdir=project_root())
        except CommandError as e:
            if 'fatal: Authentication failed' in e.stdout:
                raise ContextError('authentication failure') from e
            raise e

    assert plugin_path.is_dir(), f'plugin directory doesn\'t exist: {plugin_path}'

    repo = Repo(plugin_path.resolve())
    with wrap_context('checking out git reference'):
        if plugin_config.git_ref:
            repo.git.checkout(plugin_config.git_ref)

    if plugin_config.git_directory:
        plugin_path = (plugin_path / plugin_config.git_directory).resolve()
        assert plugin_path.is_dir(), f"can't find subdirectory: {plugin_path}"
    return plugin_path
