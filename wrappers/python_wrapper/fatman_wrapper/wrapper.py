from typing import Optional
from fastapi import FastAPI

from fatman_wrapper.api import create_api_app
from fatman_wrapper.health import HealthState
from fatman_wrapper.loader import instantiate_entrypoint
from fatman_wrapper.validate import validate_entrypoint


def create_entrypoint_app(
        model_path: str,
        class_name: Optional[str] = None,
        entrypoint_hostname: Optional[str] = None,
        health_state: HealthState = None,
) -> FastAPI:
    """
    Load entrypoint from a Python module and embed it in a FastAPI app
    """
    entrypoint = instantiate_entrypoint(
        model_path,
        class_name,
        entrypoint_hostname,
    )
    validate_entrypoint(entrypoint)
    if health_state is None:
        health_state = HealthState(live=True, ready=True)
    return create_api_app(entrypoint, health_state)
