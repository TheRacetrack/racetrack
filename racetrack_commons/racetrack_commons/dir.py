import os
from pathlib import Path


def project_root() -> Path:
    """Return project root dir"""
    return Path(os.path.abspath(__file__)).parent.parent.parent.absolute()
