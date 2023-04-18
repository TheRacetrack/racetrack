import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from dashboard.server.endpoint.account import setup_account_endpoints


def setup_api_endpoints(app: FastAPI):

    setup_account_endpoints(app)

    @app.get("/api/status")
    def _status():
        """Report current application status"""
        content = {
            'service': 'dashboard',
            'live': True,
            'ready': True,
            'git_version': os.environ.get('GIT_VERSION', 'dev'),
            'docker_tag': os.environ.get('DOCKER_TAG', ''),
        }
        return JSONResponse(content=content, status_code=200)
