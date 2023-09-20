import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse


def setup_health_endpoint(api: FastAPI):

    @api.get("/live", tags=['root'])
    def _live():
        """Report service liveness: whether it has started"""
        return {
            'service': 'dashboard',
            'live': True,
        }

    @api.get("/ready", tags=['root'])
    def _ready():
        """Report service readiness: whether it's available for accepting traffic"""
        return {
            'service': 'dashboard',
            'ready': True,
        }

    @api.get("/health", tags=['root'])
    def _health():
        """Report current application status"""
        content = {
            'service': 'dashboard',
            'live': True,
            'ready': True,
            'git_version': os.environ.get('GIT_VERSION', 'dev'),
            'docker_tag': os.environ.get('DOCKER_TAG', ''),
        }
        return JSONResponse(content=content, status_code=200)
