from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from pydantic import BaseModel, Extra

from racetrack_commons.plugin.core import PluginCore


class PluginManifest(BaseModel, extra=Extra.forbid, arbitrary_types_allowed=True):
    """Details of the contents of the plugin"""

    name: str

    version: str

    build_date: Optional[str] = None
    
    # URL of the plugin homepage
    url: Optional[str] = None

    # order in plugins sequence, lowest priority gets executed first
    priority: int = 0


@dataclass
class PluginData:
    zip_path: Path
    plugin_manifest: PluginManifest
    plugin_instance: PluginCore
