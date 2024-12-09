from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict

from racetrack_client.client_config.client_config import Credentials


class JobSecrets(BaseModel):
    """Credentials and secret env vars needed to build and deploy a job"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    git_credentials: Optional[Credentials]
    secret_build_env: Dict[str, str]
    secret_runtime_env: Dict[str, str]
