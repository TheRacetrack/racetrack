from typing import Dict, Optional

from pydantic import BaseModel

from racetrack_client.client_config.client_config import Credentials


class JobSecrets(BaseModel, arbitrary_types_allowed=True):
    """Credentials and secret env vars needed to build and deploy a job"""
    git_credentials: Optional[Credentials]
    secret_build_env: Dict[str, str]
    secret_runtime_env: Dict[str, str]
