from e2e.utils import _configure_env, _create_esc, _delete_workload, _deploy_and_verify, _wait_for_components, _install_plugin


def test_deploy_model():
    environment = _configure_env()
    _wait_for_components()

    _install_plugin('github.com/TheRacetrack/plugin-python-job-type')
    if environment == 'docker':
        _install_plugin('github.com/TheRacetrack/plugin-docker-infrastructure')
    elif environment == 'kind':
        _install_plugin('github.com/TheRacetrack/plugin-kubernetes-infrastructure')

    esc = _create_esc()

    # Wipe out older workloads, then send deploy request to Lifecycle
    _delete_workload('adder')
    _deploy_and_verify('sample/python-class', 'adder', esc)
