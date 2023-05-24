import os
import time
import pytest

from e2e.utils import PYTHON_PLUGIN_VERSION, _configure_env, _delete_workload, _deploy, _install_plugin

suite_full = pytest.mark.skipif(
    os.getenv('TEST_SUITE') != 'full', reason='TEST_SUITE value != full'
)


@suite_full
def test_deploy_delete_stress():
    _configure_env()
    _install_plugin(f'github.com/TheRacetrack/plugin-python-job-type=={PYTHON_PLUGIN_VERSION}')

    start = time.time()

    for i in range(5):
        print(" stress iteration " + str(i+1))
        _deploy('sample/python-class')
        time.sleep(3)

        _delete_workload('adder')
        time.sleep(5)

    end = time.time()
    print(f"stress testing took {end-start}s")
