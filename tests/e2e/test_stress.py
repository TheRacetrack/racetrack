import os
import time
import pytest
from racetrack_client.log.context_error import ContextError
from racetrack_commons.entities.job_client import JobRegistryClient

from e2e.utils import ADMIN_AUTH_TOKEN, _configure_env, _delete_workload, _deploy, _install_plugin

suite_full = pytest.mark.skipif(
    os.getenv('TEST_SUITE') != 'full', reason='TEST_SUITE value != full'
)


@suite_full
def test_deploy_delete_stress():
    _configure_env()
    _install_plugin('github.com/TheRacetrack/plugin-python-job-type')

    start = time.time()

    for i in range(5):
        print(" stress iteration " + str(i+1))
        _deploy('sample/python-class')
        for j in range(3):
            _search_for_orphaned_jobs()
            time.sleep(1)

        _delete_workload('adder')
        for j in range(5):
            _search_for_orphaned_jobs()
            time.sleep(1)

    end = time.time()
    print(f"stress testing took {end-start}s")


def _search_for_orphaned_jobs():
    frc = JobRegistryClient(auth_token=ADMIN_AUTH_TOKEN)
    jobs = frc.list_deployed_jobs()
    for job in jobs:
        if job.status == "orphaned":
            raise ContextError('found orphaned')
