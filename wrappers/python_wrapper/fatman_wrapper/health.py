import os
from typing import Tuple, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse


class HealthState:
    """Liveness and Readiness state of the app shared between workers"""

    def __init__(self, live: bool = True, ready: bool = False):
        self._live = live
        self._ready = ready
        self._error: Optional[str] = None

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def live(self) -> bool:
        return self._live

    @property
    def error(self) -> Optional[str]:
        return self._error

    def set_ready(self):
        self._ready = True

    def set_error(self, error: str):
        self._live = False
        self._error = error

    def live_response(self) -> Tuple[Dict, int]:
        """
        :return: liveness response in a tuple format: JSON output, HTTP status code
        """
        if self.live:
            return {
                'live': True,
                'deployment_timestamp': os.environ.get('FATMAN_DEPLOYMENT_TIMESTAMP'),
            }, 200
        else:
            return {
                'live': False,
                'deployment_timestamp': os.environ.get('FATMAN_DEPLOYMENT_TIMESTAMP'),
                'error': self.error,
            }, 500

    def ready_response(self) -> Tuple[Dict, int]:
        """
        :return: readiness response in a tuple format: JSON output, HTTP status code
        """
        if self.ready:
            return {'ready': True}, 200
        else:
            return {'ready': False}, 500

    def health_response(self, fatman_name: str) -> Tuple[Dict, int]:
        """
        :return: health response in a tuple format: JSON output, HTTP status code
        """
        result = {
            'service': 'fatman',
            'fatman_name': fatman_name,
            'live': self.live,
            'ready': self.ready,
            'status': 'pass' if self.ready else 'fail',
            'error': self.error,
            'fatman_version': os.environ.get('FATMAN_VERSION'),
            'git_version': os.environ.get('GIT_VERSION'),
            'deployed_by_racetrack_version': os.environ.get('DEPLOYED_BY_RACETRACK_VERSION'),
            'deployment_timestamp': os.environ.get('FATMAN_DEPLOYMENT_TIMESTAMP'),
        }
        return result, 200 if self.live and self.ready else 500


def setup_health_endpoints(api: FastAPI, health_state: HealthState, fatman_name: str):

    @api.get("/health", tags=['root'])
    async def _health():
        """Report current aggregated application status"""
        content, status = health_state.health_response(fatman_name)
        return JSONResponse(content=content, status_code=status)

    @api.get("/live", tags=['root'])
    async def _live():
        """Report application liveness: whether it has started (but might not be ready yet)"""
        content, status = health_state.live_response()
        return JSONResponse(content=content, status_code=status)

    @api.get("/ready", tags=['root'])
    async def _ready():
        """Report application readiness: whether it's available for accepting traffic"""
        content, status = health_state.ready_response()
        return JSONResponse(content=content, status_code=status)
