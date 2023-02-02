from dataclasses import dataclass
from typing import List
import pytest

from racetrack_client.utils.semver import SemanticVersion, SemanticVersionPattern


def test_parse_semver():
    assert str(SemanticVersion('1.2.3')) == '1.2.3'
    assert str(SemanticVersion('10.0.1-alpha')) == '10.0.1-alpha'
    assert str(SemanticVersion('0.0.0-dev')) == '0.0.0-dev'
    assert str(SemanticVersion('1.2.3.4')) == '1.2.3.4'
    assert str(SemanticVersion('1500.100.900')) == '1500.100.900'

    semver = SemanticVersion('1.200.3-alpha')
    assert semver.major == 1
    assert semver.minor == 200
    assert semver.patch == 3
    assert semver.label == '-alpha'


def test_invalid_semver():
    with pytest.raises(ValueError) as excinfo:
        SemanticVersion('1.0')
    assert str(excinfo.value) == "Version '1.0' doesn't match SemVer format 'X.Y.Z[-label]'"

    with pytest.raises(ValueError) as excinfo:
        SemanticVersion('1.0.a')
    with pytest.raises(ValueError) as excinfo:
        SemanticVersion('dev')


def test_version_ordering():
    versions = [
        '1.0.0',
        '0.0.1-rc2',
        '0.0.0',
        '0.2.0',
        '0.0.0rc1',
        '0.0.1',
        '0.0.1-alpha',
        '10.0.0',
        '0.0.1-dev',
        '0.0.10',
    ]

    versions.sort(key=lambda ver: SemanticVersion(ver))

    assert versions == [
        '0.0.0rc1',
        '0.0.0',
        '0.0.1-alpha',
        '0.0.1-dev',
        '0.0.1-rc2',
        '0.0.1',
        '0.0.10',
        '0.2.0',
        '1.0.0',
        '10.0.0',
    ], 'Versions are sorted according to SemVer rules'


def test_get_latest_stable_version():
    @dataclass
    class Job:
        name: str
        version: str

    jobs: List[Job] = [
        Job('adder', '0.0.1'),
        Job('adder', '0.2.0'),
        Job('adder', '0.3.0-dev'),
    ]

    latest_job = SemanticVersion.find_latest_stable(jobs, key=lambda f: f.version)
    assert latest_job == Job('adder', '0.2.0'), 'latest stable ignores "-dev" versions'

    assert SemanticVersion.find_latest_stable([], key=lambda f: f.version) is None


def test_get_latest_version_wildcard():
    @dataclass
    class Job:
        name: str
        version: str

    jobs: List[Job] = [
        Job('adder', '1.0.1'),
        Job('adder', '2.0.0'),
        Job('adder', '2.0.4'),
        Job('adder', '2.1.5'),
        Job('adder', '2.2.2-dev'),
        Job('adder', '3.3.0'),
        Job('adder', '1500.100.900'),
    ]

    pattern = SemanticVersionPattern('2.x')
    latest_job = SemanticVersion.find_latest_wildcard(pattern, jobs, key=lambda f: f.version)
    assert latest_job == Job('adder', '2.1.5'), 'A.x pattern finds highest stable major version'

    pattern = SemanticVersionPattern('2.x.x')
    latest_job = SemanticVersion.find_latest_wildcard(pattern, jobs, key=lambda f: f.version)
    assert latest_job == Job('adder', '2.1.5'), 'A.x.x pattern finds highest stable major version'

    pattern = SemanticVersionPattern('2.0.x')
    latest_job = SemanticVersion.find_latest_wildcard(pattern, jobs, key=lambda f: f.version)
    assert latest_job == Job('adder', '2.0.4'), 'A.B.x pattern finds highest minor version'

    pattern = SemanticVersionPattern('x')
    latest_job = SemanticVersion.find_latest_wildcard(pattern, jobs, key=lambda f: f.version)
    assert latest_job == Job('adder', '1500.100.900'), 'x pattern returns latest'

    pattern = SemanticVersionPattern('x.x.x')
    latest_job = SemanticVersion.find_latest_wildcard(pattern, jobs, key=lambda f: f.version)
    assert latest_job == Job('adder', '1500.100.900'), 'x.x.x pattern returns latest'


def test_valid_semver_pattern():
    SemanticVersionPattern('1.0.x')
    SemanticVersionPattern('1.x')
    SemanticVersionPattern('1.x.x')
    SemanticVersionPattern('91.1005.x')

    assert SemanticVersionPattern.is_wildcard_pattern('91.1005.x')
    assert SemanticVersionPattern.is_wildcard_pattern('x.x.x')
    assert SemanticVersionPattern.is_wildcard_pattern('x')


def test_invalid_semver_pattern():
    with pytest.raises(ValueError) as excinfo:
        SemanticVersionPattern('1.0.2')
    with pytest.raises(ValueError) as excinfo:
        SemanticVersionPattern('1.2x')
    with pytest.raises(ValueError) as excinfo:
        SemanticVersionPattern('1.x2')
    with pytest.raises(ValueError) as excinfo:
        SemanticVersionPattern('dev')
    with pytest.raises(ValueError) as excinfo:
        SemanticVersionPattern('dev')

    assert not SemanticVersionPattern.is_wildcard_pattern('1.0.0')
    assert not SemanticVersionPattern.is_wildcard_pattern('1.x-dev')
    assert not SemanticVersionPattern.is_wildcard_pattern('1.0.0-x')
    assert not SemanticVersionPattern.is_wildcard_pattern('dex')
