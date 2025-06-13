import os

from fastapi import APIRouter

from lifecycle.config import Config
from racetrack_commons.urls import get_external_pub_url, get_external_lifecycle_url, get_external_grafana_url


def setup_info_endpoints(api: APIRouter, config: Config):

    @api.get('/info')
    def _info():
        """Report current configuration status"""
        return {
            'service': 'lifecycle',
            'git_version': os.environ.get('GIT_VERSION', 'dev'),
            'docker_tag': os.environ.get('DOCKER_TAG', ''),
            'auth_required': config.auth_required,
            'external_pub_url': get_external_pub_url(config.external_pub_url),
            'lifecycle_url': get_external_lifecycle_url(),
            'grafana_url': get_external_grafana_url(),
        }
