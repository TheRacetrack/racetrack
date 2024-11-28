import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from lifecycle.config import Config
from lifecycle.server.cache import LifecycleCache


def setup_health_endpoint(api: FastAPI, config: Config):

    @api.get("/live", tags=['root'])
    def _live():
        """Report service liveness: whether it has started"""
        return {
            'service': 'lifecycle',
            'live': True,
        }

    @api.get("/ready", tags=['root'])
    def _ready():
        """Report service readiness: whether it's available for accepting traffic"""
        return {
            'service': 'lifecycle',
            'ready': True,
        }

    @api.get("/health", tags=['root'])
    def _health():
        """Report current application status"""
        database_connected = LifecycleCache.db_engine().database_status().connected
        status_code = 200 if database_connected else 500
        content = {
            'service': 'lifecycle',
            'live': True,
            'database_connected': database_connected,
            'git_version': os.environ.get('GIT_VERSION', 'dev'),
            'docker_tag': os.environ.get('DOCKER_TAG', ''),
            'auth_required': config.auth_required,
        }
        return JSONResponse(content=content, status_code=status_code)
