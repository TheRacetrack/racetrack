import os
from typing import Tuple, Dict

from racetrack_client.log.context_error import ContextError
from racetrack_client.utils.shell import shell


def health_response() -> Tuple[Dict, int]:
    """
    :return: health response in a tuple format: JSON output, HTTP status code
    """
    result = {
        'service': 'image-builder',
        'git_version': os.environ.get('GIT_VERSION', 'dev'),
        'docker_tag': os.environ.get('DOCKER_TAG', ''),
    }

    try:
        result['status'] = 'pass' if check() else 'warn'
        status_code = 200
    except Exception as e:
        result['status'] = 'fail'
        result['details'] = str(e)
        status_code = 500
    return result, status_code


def check() -> bool:
    """
    Check application health.
    on failure - raise error
    on pass - return True
    on warn - return False
    """
    try:
        shell('docker ps', print_stdout=False, print_log=False)
    except Exception as e:
        raise ContextError('docker daemon not ready') from e

    return True
