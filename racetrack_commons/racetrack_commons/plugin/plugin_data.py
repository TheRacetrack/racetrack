from pathlib import Path
from dataclasses import dataclass

from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_commons.plugin.core import PluginCore


@dataclass
class PluginData:
    zip_path: Path
    plugin_manifest: PluginManifest
    plugin_instance: PluginCore
    config_path: Path
