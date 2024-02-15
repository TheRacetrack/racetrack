from typing import Dict

from pydantic import BaseModel, ConfigDict


class Credentials(BaseModel):
    username: str
    password: str


class ClientConfig(BaseModel):
    """Global options for a local client"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # default URL of Racetrack API server (Lifecycle URL)
    lifecycle_url: str = 'http://127.0.0.1:7002'

    # Git auth credentials set for particular repositories
    git_credentials: Dict[str, Credentials] = {}

    # Racetrack URL aliases: alias name -> full URL to Lifecycle API
    lifecycle_url_aliases: Dict[str, str] = {}

    # Auth tokens per Lifecycle URL
    user_auths: Dict[str, str] = {}
