from pathlib import Path
import random
import shutil
import tempfile
import threading
from typing import Any, Callable, Iterable
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from racetrack_commons.plugin.loader import load_plugin_from_zip, load_plugins_from_dir, EXTRACTED_PLUGINS_DIR
from racetrack_commons.plugin.plugin_data import PluginData
from racetrack_client.log.context_error import wrap_context, ContextError
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_client.utils.time import now, datetime_to_timestamp

logger = get_logger(__name__)
LAST_CHANGE_FILE = 'last-change.txt'


class PluginEngine:
    def __init__(self, plugins_dir: str | None = None):
        self.plugins_data: list[PluginData] = []
        self.last_change_timestamp: int = 0
        if plugins_dir:
            self.plugins_dir: str = plugins_dir
            try:
                self._load_plugins()
            except BaseException as e:
                log_exception(e)
            self._watch_plugins_changes()

    def _load_plugins(self):
        start_time = time.time()
        with wrap_context('Loading plugins'):
            self.plugins_data = load_plugins_from_dir(self.plugins_dir)
            if self.plugins_data:
                duration = time.time() - start_time
                plugin_plural = 'plugin' if len(self.plugins_data) == 1 else 'plugins'
                plugins_list_str = ', '.join([f'{p.plugin_manifest.name} ({p.plugin_manifest.version})' for p in self.plugins_data])
                logger.info(f'{len(self.plugins_data)} {plugin_plural} have been loaded in {duration:.2f}s: {plugins_list_str}')
            else:
                logger.info(f'No plugins to load')

    def invoke_plugin_hook(self, function: Callable, *args, **kwargs) -> list[Any]:
        """
        Invoke a hook function in all plugins
        :param function: PluginCore function to invoke
        :param args: positional arguments to pass to the function
        :param kwargs: keyword arguments to pass to the function
        :return: list of return values from each plugin
        """
        function_name = function.__name__
        results = []
        for plugin_data in self.plugins_data:
            if hasattr(plugin_data.plugin_instance, function_name):
                with wrap_context(f'Invoking hook "{function_name}" of plugin {plugin_data.plugin_manifest.name} {plugin_data.plugin_manifest.version}',
                                  log_debug=True):
                    result = getattr(plugin_data.plugin_instance, function_name)(*args, **kwargs)
                    results.append(result)
        return results

    def invoke_one_plugin_hook(self, plugin_name: str, function: Callable, *args, **kwargs) -> Any:
        """
        Invoke a hook function for one plugin
        :param plugin_name: name of the plugin
        :param function: PluginCore function to invoke
        :param args: positional arguments to pass to the function
        :param kwargs: keyword arguments to pass to the function
        """
        function_name = function.__name__
        plugin_data = self.find_plugin(plugin_name)
        if hasattr(plugin_data.plugin_instance, function_name):
            with wrap_context(f'Invoking hook "{function_name}" of plugin {plugin_data.plugin_manifest.name} {plugin_data.plugin_manifest.version}',
                              log_debug=True):
                return getattr(plugin_data.plugin_instance, function_name)(*args, **kwargs)
        else:
            logger.warning(f'Plugin {plugin_name} does not have hook {function_name}')
            return None

    def invoke_associated_plugin_hook(self, function: Callable, *args, **kwargs) -> dict[PluginManifest, Any]:
        """
        Invoke a hook function in all plugins and associate the results with the plugins' manifests
        :param function: PluginCore function to invoke
        :param args: positional arguments to pass to the function
        :param kwargs: keyword arguments to pass to the function
        :return: dict of plugins' manifests mapped to the return value from each plugin
        """
        function_name = function.__name__
        results: dict[PluginManifest, Any] = {}
        for plugin_data in self.plugins_data:
            if hasattr(plugin_data.plugin_instance, function_name):
                with wrap_context(f'Invoking hook "{function_name}" of plugin {plugin_data.plugin_manifest.name} {plugin_data.plugin_manifest.version}',
                                  log_debug=True):
                    result = getattr(plugin_data.plugin_instance, function_name)(*args, **kwargs)
                    results[plugin_data.plugin_manifest] = result
        return results

    def find_plugin(self, name: str, version: str | None = None) -> PluginData:
        if version:
            for plugin_data in self.plugins_data:
                if plugin_data.plugin_manifest.name == name and plugin_data.plugin_manifest.version == version:
                    return plugin_data
            raise EntityNotFound(f'plugin named "{name}" {version} was not found')

        else:
            plugin_versions = [plugin_data for plugin_data in self.plugins_data
                               if plugin_data.plugin_manifest.name == name]
            if not plugin_versions:
                raise EntityNotFound(f'plugin named "{name}" was not found')
            return plugin_versions[-1]

    def find_plugins(self, name: str, version: str | None = None) -> Iterable[PluginData]:
        for plugin_data in self.plugins_data:
            if plugin_data.plugin_manifest.name == name and (not version or plugin_data.plugin_manifest.version == version):
                yield plugin_data

    def _watch_plugins_changes(self):
        """
        Watch for changes in plugins dir and reload plugins if change happens.
        It monitors the flag file last-change.txt which is updated AFTER
        uploading and extraction is completed to prevent from loading inconsistent files.
        """
        self.last_change_timestamp = self._read_last_change_timestamp()
        if self.last_change_timestamp == 0:
            self._record_last_change()

        def compare_changes():
            try:
                new_timestamp = self._read_last_change_timestamp()
                if self.last_change_timestamp != new_timestamp:
                    self.last_change_timestamp = new_timestamp
                    logger.info('Plugins modification detected, reloading plugins...')
                    self._load_plugins()
            except BaseException as e:
                log_exception(ContextError('checking plugin changes', e))

        class ChangesHandler(FileSystemEventHandler):
            def on_created(self, event):
                if Path(event.src_path).name == LAST_CHANGE_FILE:
                    logger.debug(f'file creation notified on {event.src_path}')
                    compare_changes()

            def on_deleted(self, event):
                if Path(event.src_path).name == LAST_CHANGE_FILE:
                    logger.debug(f'file deletion notified on {event.src_path}')
                    compare_changes()

            def on_modified(self, event):
                if Path(event.src_path).name == LAST_CHANGE_FILE:
                    logger.debug(f'file modification notified on {event.src_path}')
                    compare_changes()

            def on_moved(self, event):
                if Path(event.src_path).name == LAST_CHANGE_FILE:
                    logger.debug(f'file moving notified on {event.src_path}')
                    compare_changes()

        event_handler = ChangesHandler()
        observer = Observer()
        observer.schedule(event_handler, path=Path(self.plugins_dir).as_posix(), recursive=False)
        observer.start()

        # inotify may not work on network filesystems
        def _check_periodically():
            while True:
                time.sleep(60)
                compare_changes()

        threading.Thread(target=_check_periodically, daemon=True).start()

    def upload_plugin(self, filename: str, file_bytes: bytes, replace: bool = False) -> PluginManifest:
        """
        Upload and load a plugin
        :param filename: name of the file
        :param file_bytes: bytes of the file
        :param replace: whether to replace the older versions - delete the existing versions with the same name
        :return: PluginManifest of the uploaded plugin
        """
        tmp_dir = Path(tempfile.mkdtemp(prefix='racetrack-uploaded-plugin-'))
        try:
            assert Path(filename).suffix == '.zip', '.zip plugins are only supported'

            # save to tmp.zip to avoid overwriting current plugins
            tmp_zip = tmp_dir / f'tmp_{random.randint(0, 999999)}.zip'
            if not tmp_zip.is_file():
                tmp_zip.touch()
                try:
                    tmp_zip.chmod(mode=0o666)
                except PermissionError:
                    logger.warning(f'Can\'t change permissions of file {tmp_zip}')
            tmp_zip.write_bytes(file_bytes)
            
            plugin_data = load_plugin_from_zip(tmp_zip)
            plugin_name = plugin_data.plugin_manifest.name
            plugin_version = plugin_data.plugin_manifest.version

            if replace:
                self._delete_older_plugins(plugin_name)
            else:
                self._delete_older_plugin_version(plugin_name, plugin_version)
            shutil.move(tmp_zip, Path(self.plugins_dir) / filename)
            logger.info(f'Plugin {plugin_name} has been uploaded from {filename}')

        finally:
            shutil.rmtree(tmp_dir)

        self._load_plugins()
        self._record_last_change()
        return plugin_data.plugin_manifest

    def read_plugin_config(self, name: str, version: str) -> str:
        plugin_data = self.find_plugin(name, version)
        config_data = Path(plugin_data.config_path).read_text()
        return config_data

    def write_plugin_config(self, name: str, version: str, config: str):
        plugin_data = self.find_plugin(name, version)
        plugin_data.config_path.write_text(config)
        logger.info(f'Plugin config ({name} {version}) has been overwritten: {plugin_data.config_path}')
        self._record_last_change()
        self._load_plugins()
        
    def delete_plugin_by_version(self, name: str, version: str):
        plugin_data = self.find_plugin(name, version)
        self._delete_plugin(plugin_data)
        logger.info(f'Plugin {plugin_data.plugin_manifest.name} {plugin_data.plugin_manifest.version} ({plugin_data.zip_path}) has been deleted')
        self._record_last_change()
        self._load_plugins()

    def _delete_older_plugin_version(self, plugin_name: str, plugin_version: str):
        try:
            plugin_data = self.find_plugin(plugin_name, plugin_version)
            self._delete_plugin(plugin_data)
            logger.info(f'Older plugin version has been deleted: {plugin_data.zip_path.name}')
        except EntityNotFound:
            return

    def _delete_older_plugins(self, plugin_name: str):
        plugins_data = self.find_plugins(plugin_name)
        for plugin_data in plugins_data:
            self._delete_plugin(plugin_data)
            logger.info(f'Older plugin version has been deleted: {plugin_data.zip_path.name}')

    def _delete_plugin(self, plugin_data: PluginData):
        if plugin_data.zip_path.is_file():
            plugin_data.zip_path.unlink()
        else:
            logger.warning(f'ZIP plugin was not found: {plugin_data.zip_path}')

        extracted_dir = Path(self.plugins_dir) / EXTRACTED_PLUGINS_DIR / plugin_data.zip_path.stem
        if extracted_dir.is_dir():
            shutil.rmtree(extracted_dir)
        else:
            logger.warning(f'extracted plugin directory was not found: {extracted_dir}')

    def _read_last_change_timestamp(self) -> int:
        change_file = Path(self.plugins_dir) / LAST_CHANGE_FILE
        if not change_file.is_file():
            return 0
        txt = change_file.read_text()
        if not txt:
            return 0
        return int(txt.strip())
    
    def _record_last_change(self):
        self.last_change_timestamp = datetime_to_timestamp(now())
        change_file = Path(self.plugins_dir) / LAST_CHANGE_FILE
        if not change_file.is_file():
            change_file.touch()
            try:
                change_file.chmod(mode=0o666)
            except PermissionError:
                logger.warning(f'Can\'t change permissions of file {change_file}')
        change_file.write_text(f'{self.last_change_timestamp}')

    @property
    def plugin_manifests(self) -> list[PluginManifest]:
        return [p.plugin_manifest for p in self.plugins_data]
