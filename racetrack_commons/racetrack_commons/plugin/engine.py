from pathlib import Path
import shutil
import threading
from typing import Callable, List, Optional
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from racetrack_commons.plugin.loader import load_plugin_from_zip, load_plugins_from_dir, EXTRACTED_PLUGINS_DIR
from racetrack_commons.plugin.plugin_manifest import PluginData, PluginManifest
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.time import now, datetime_to_timestamp

logger = get_logger(__name__)
LAST_CHANGE_FILE = 'last-change.txt'


class PluginEngine:
    def __init__(self, plugins_dir: Optional[str] = None):
        self.plugins_data: List[PluginData] = []
        self.last_change_timestamp: int = 0
        if plugins_dir:
            self.plugins_dir: str = plugins_dir
            self._load_plugins()
            self._watch_plugins_changes()

    def _load_plugins(self):
        start_time = time.time()
        with wrap_context('Loading plugins'):
            self.plugins_data = load_plugins_from_dir(self.plugins_dir)
            if self.plugins_data:
                duration = time.time() - start_time
                plugin_plural = 'plugin' if len(self.plugins_data) == 1 else 'plugins'
                logger.info(f'{len(self.plugins_data)} {plugin_plural} have been loaded in {duration:.2f}s')

    def invoke_plugin_hook(self, function: Callable, *args, **kwargs) -> List:
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
                with wrap_context(f'Invoking hook {function_name} from plugin {plugin_data.plugin_manifest.name}'):
                    logger.debug(f'Invoking hook {function_name} from plugin {plugin_data.plugin_manifest.name}')
                    result = getattr(plugin_data.plugin_instance, function_name)(*args, **kwargs)
                    results.append(result)
        return results

    def invoke_one_plugin_hook(self, plugin_name: str, function: Callable, *args, **kwargs):
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
            with wrap_context(f'Invoking hook {function_name} from plugin {plugin_data.plugin_manifest.name}'):
                logger.debug(f'Invoking hook {function_name} from plugin {plugin_data.plugin_manifest.name}')
                return getattr(plugin_data.plugin_instance, function_name)(*args, **kwargs)
        else:
            logger.warning(f'Plugin {plugin_name} does not have hook {function_name}')
            return None

    def find_plugin(self, name: str, version: Optional[str] = None) -> PluginData:
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
            new_timestamp = self._read_last_change_timestamp()
            if self.last_change_timestamp != new_timestamp:
                self.last_change_timestamp = new_timestamp
                logger.info('Plugins modification detected, reloading plugins...')
                self._load_plugins()

        class ChangesHandler(FileSystemEventHandler):
            def on_created(self, event):
                if Path(event.src_path).name == LAST_CHANGE_FILE:
                    logger.debug(f'file creation notified on {event.src_path}')
                    threading.Thread(target=compare_changes, daemon=True).start()

            def on_deleted(self, event):
                if Path(event.src_path).name == LAST_CHANGE_FILE:
                    logger.debug(f'file deletion notified on {event.src_path}')
                    threading.Thread(target=compare_changes, daemon=True).start()

            def on_modified(self, event):
                if Path(event.src_path).name == LAST_CHANGE_FILE:
                    logger.debug(f'file modification notified on {event.src_path}')
                    threading.Thread(target=compare_changes, daemon=True).start()

            def on_moved(self, event):
                if Path(event.src_path).name == LAST_CHANGE_FILE:
                    logger.debug(f'file moving notified on {event.src_path}')
                    threading.Thread(target=compare_changes, daemon=True).start()

        event_handler = ChangesHandler()
        observer = Observer()
        observer.schedule(event_handler, path=Path(self.plugins_dir).as_posix(), recursive=False)
        observer.start()

    def upload_plugin(self, filename: str, file_bytes: bytes):
        target_zip = Path(self.plugins_dir) / filename
        assert target_zip.suffix == '.zip', '.zip plugins are only supported'

        # save to tmp.zip to avoid overwriting current plugins
        tmp_zip = Path(self.plugins_dir) / 'tmp.zip'
        tmp_zip.write_bytes(file_bytes)
        plugin_data = load_plugin_from_zip(tmp_zip)
        plugin_name = plugin_data.plugin_manifest.name
        plugin_version = plugin_data.plugin_manifest.version

        tmp_extracted_dir = Path(self.plugins_dir) / EXTRACTED_PLUGINS_DIR / tmp_zip.stem
        shutil.rmtree(tmp_extracted_dir)

        self._delete_older_plugin_version(plugin_name, plugin_version)
        tmp_zip.rename(target_zip)
        logger.info(f'Plugin {plugin_name} has been uploaded from {filename}')

        self._load_plugins()
        self._record_last_change()
        
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

    def _delete_plugin(self, plugin_data: PluginData):
        if not plugin_data.zip_path.is_file():
            logger.warning(f'ZIP plugin was not found: {plugin_data.zip_path}')
        plugin_data.zip_path.unlink()

        extracted_dir = Path(self.plugins_dir) / EXTRACTED_PLUGINS_DIR / plugin_data.zip_path.stem
        if not extracted_dir.is_dir():
            logger.warning(f'extracted plugin directory was not found: {extracted_dir}')
        shutil.rmtree(extracted_dir)

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
        change_file.write_text(f'{self.last_change_timestamp}')

    @property
    def plugin_manifests(self) -> List[PluginManifest]:
        return [p.plugin_manifest for p in self.plugins_data]
