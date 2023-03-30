import os

from fastapi import APIRouter

from lifecycle.config import Config


def setup_info_endpoints(api: APIRouter, config: Config):

    @api.get('/info')
    async def _info():
        """Report current configuration status"""
        return {
            'service': 'lifecycle',
            'git_version': os.environ.get('GIT_VERSION', 'dev'),
            'docker_tag': os.environ.get('DOCKER_TAG', ''),
            'auth_required': config.auth_required,
        }
