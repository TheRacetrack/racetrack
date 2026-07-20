from racetrack_client.utils.shell import shell_output


def test_cli_help():  # smoke test
    output = shell_output('racetrack')
    assert 'CLI client tool for managing workloads in Racetrack' in output
    output = shell_output('racetrack deploy --help')
    assert 'Send request deploying a Job to the Racetrack cluster' in output
