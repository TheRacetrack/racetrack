from typing import Optional

from pydantic import BaseModel


class PluginManifest(BaseModel):
    """Details of the contents of the plugin"""

    name: str

    version: str

    build_date: Optional[str] = None
    
    # URL of the plugin homepage
    url: Optional[str] = None

    # order in plugins sequence, lowest priority gets executed first
    priority: int = 0
