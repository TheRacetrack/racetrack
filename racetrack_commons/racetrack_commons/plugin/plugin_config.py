from typing import Optional

from pydantic import BaseModel


class PluginConfig(BaseModel):
    """Configuration of Racetrack plugin"""

    # Name of the plugin
    name: str

    # git remote url to the plugin module
    git_remote: str
    
    # git branch or commit hash describing plugin version
    git_ref: Optional[str] = None

    # subdirectory where the plugin is stored in the git repository
    git_directory: Optional[str] = None

    # order in plugins sequence, lowest priority gets executed first
    priority: int = 0
