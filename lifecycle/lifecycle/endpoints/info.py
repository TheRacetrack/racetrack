import os

from fastapi import APIRouter

from racetrack_client.utils.request import Requests, parse_response_object
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.config import Config


def setup_info_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):

    @api.get('/info')
    async def _info():
        """Report current configuration status"""
        return {
            'service': 'lifecycle',
            'git_version': os.environ.get('GIT_VERSION', 'dev'),
            'docker_tag': os.environ.get('DOCKER_TAG', ''),
            'auth_required': config.auth_required,
        }

    @api.get('/job_type/versions')
    def _get_job_type_versions():
        """List available job type versions"""
        r = Requests.get(
            f'{config.image_builder_url}/api/v1/job_type/versions',
        )
        return parse_response_object(r, 'Image builder API error')
