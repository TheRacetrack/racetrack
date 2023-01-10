from typing import Dict

from pydantic import BaseModel


class Credentials(BaseModel):
    username: str
    password: str


class ClientConfig(BaseModel, arbitrary_types_allowed=True):
    """Global options for a local client"""

    # default URL of Racetrack API server (Lifecycle URL)
    lifecycle_url: str = 'http://localhost:7002'

    # Git auth credentials set for particular repositories
    git_credentials: Dict[str, Credentials] = {}

    # Racetrack URL aliases: alias name -> full URL to Lifecycle API
    lifecycle_url_aliases: Dict[str, str] = {}

    # Auth tokens per Lifecycle URL
    user_auths: Dict[str, str] = {}
