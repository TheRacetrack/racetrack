from e2e.utils import DOCKER_PLUGIN_VERSION, K8S_PLUGIN_VERSION, PYTHON_PLUGIN_VERSION, _configure_env, _create_esc, _delete_workload, _deploy_and_verify, _wait_for_components, _install_plugin


def test_deploy_model():
    environment = _configure_env()
    _wait_for_components()

    _install_plugin(f'github.com/TheRacetrack/plugin-python-job-type=={PYTHON_PLUGIN_VERSION}')
    if environment == 'docker':
        _install_plugin(f'github.com/TheRacetrack/plugin-docker-infrastructure=={DOCKER_PLUGIN_VERSION}')
    elif environment == 'kind':
        _install_plugin(f'github.com/TheRacetrack/plugin-kubernetes-infrastructure=={K8S_PLUGIN_VERSION}')

    esc = _create_esc()

    # Wipe out older workloads, then send deploy request to Lifecycle
    _delete_workload('adder')
    _deploy_and_verify('sample/python-class', 'adder', esc)
