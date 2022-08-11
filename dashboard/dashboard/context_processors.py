import os
from typing import Dict

from django.conf import settings

from racetrack_commons.urls import get_external_lifecycle_url


def racetrack_version_context(request) -> Dict[str, str]:
    """Add Racetrack Dashboard version name to the context of all views"""
    git_version = os.environ.get('GIT_VERSION')
    docker_tag = os.environ.get('DOCKER_TAG')
    site_name = os.environ.get('SITE_NAME', '')
    return {
        'racetrack_version': f'version {docker_tag} ({git_version})',
        'racetrack_auth_required': settings.AUTH_REQUIRED,
        'lifecycle_url': get_external_lifecycle_url(),
        'site_name': site_name,
        'site_name_prefix': _site_name_prefix(site_name),
        'site_background': _site_background(site_name),
    }


def _site_name_prefix(site_name: str) -> str:
    if not site_name:
        return ''
    return f'[{site_name}] '


def _site_background(site_name: str) -> str:
    site_name = site_name.lower()
    if site_name == 'test':
        return '#005c14'
    elif site_name == 'preprod':
        return '#bd5f00'
    elif site_name == 'prod':
        return '#7a0000'
    return '#212529'
