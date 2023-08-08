from typing import Optional

from pydantic import BaseModel, Extra


class PluginManifest(BaseModel, extra=Extra.forbid, arbitrary_types_allowed=True):
    """Details of the contents of the plugin"""

    name: str

    version: str

    build_date: Optional[str] = None
    
    # URL of the plugin homepage
    url: Optional[str] = None

    # order in plugins sequence, lowest priority gets executed first
    priority: int = 0

    # kind of the plugin, e.g. 'infrastructure', 'job-type' or 'core'
    category: Optional[str] = None

    # list of Racetrack components that the plugin should be running on, e.g. 'lifecycle', 'image-builder'
    components: list[str] = []

    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))
