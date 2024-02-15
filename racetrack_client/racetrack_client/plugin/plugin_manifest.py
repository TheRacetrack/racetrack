from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class PluginManifest(BaseModel):
    """Details of the contents of the plugin"""
    model_config = ConfigDict(extra='forbid', arbitrary_types_allowed=True)

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
    components: List[str] = []

    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))
