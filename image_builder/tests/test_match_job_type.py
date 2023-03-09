
from racetrack_commons.deploy.job_type import match_job_type_version


def test_match_job_type_version():
    assert match_job_type_version('python3:2.6.1', ['python3:2.5.1', 'python3:2.6.1']) == 'python3:2.6.1'
    assert match_job_type_version('python3:2.6.*', [
        'python3:2.6.1', 'python3:2.6.12', 'python3:2.6.2', 'go:2.6.9',
    ]) == 'python3:2.6.12'
    assert match_job_type_version('labber:1.30.*-3.9-bullseye', [
        'labber:1.30.1-3.9-bullseye', 'labber:1.30.9-3.8-bullseye', 'labber:1.30.99-3.9-buster',
    ]) == 'labber:1.30.1-3.9-bullseye'
