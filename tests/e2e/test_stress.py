import os
import time
import pytest
from racetrack_client.log.context_error import ContextError
from racetrack_commons.entities.fatman_client import FatmanRegistryClient

from e2e.utils import ADMIN_AUTH_TOKEN, _configure_env, _delete_workload, _deploy

suite_full = pytest.mark.skipif(
    os.getenv('TEST_SUITE') != 'full', reason='TEST_SUITE value != full'
)


@suite_full
def test_deploy_delete_stress():
    _configure_env()
    start = time.time()

    for i in range(5):
        print(" stress iteration " + str(i+1))
        _deploy('sample/python-class')
        for j in range(3):
            _search_for_orphaned_fatmen()
            time.sleep(1)

        _delete_workload('adder')
        for j in range(5):
            _search_for_orphaned_fatmen()
            time.sleep(1)

    end = time.time()
    print(f"stress testing took {end-start}s")


def _search_for_orphaned_fatmen():
    frc = FatmanRegistryClient(auth_token=ADMIN_AUTH_TOKEN)
    fatmen = frc.list_deployed_fatmen()
    for fatman in fatmen:
        if fatman.status == "orphaned":
            raise ContextError('found orphaned')
