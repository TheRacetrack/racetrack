from e2e.utils import _configure_env, _create_esc, _delete_workload, _deploy_and_verify, _wait_for_components, _install_plugin


def test_deploy_model():
    environment = _configure_env()
    _wait_for_components()

    _install_plugin('/home/thokik/Repos/plugin-python-job-type/python3-job-type-2.5.11.zip')
    if environment == 'docker':
        _install_plugin('/home/thokik/Repos/plugin-docker-daemon-deployer/docker-daemon-deployer-1.4.1.zip')
    elif environment == 'kind':
        _install_plugin('/home/thokik/Repos/plugin-kubernetes-infrastructure/kubernetes-infrastructure-1.1.0.zip')

    esc = _create_esc()

    # Wipe out older workloads, then send deploy request to Lifecycle
    _delete_workload('adder')
    _deploy_and_verify('sample/python-class', 'adder', esc)
