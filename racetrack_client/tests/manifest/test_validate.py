import os
import shutil
import tempfile
from pathlib import Path

import pytest

from racetrack_client.manifest.manifest import Manifest
from racetrack_client.manifest.validate import load_validated_manifest
from racetrack_client.utils.quantity import Quantity


def test_valid_manifest_file():
    validate_tmp_manifest("""
name: golang-function
owner_email: nobody@example.com
lang: golang:latest

git:
  remote: https://github.com/TheRacetrack/racetrack
  directory: sample/golang-function
""")


def test_read_manifest_fields():
    manifest = validate_tmp_manifest("""
name: golang-function
owner_email: nobody@example.com
lang: golang:latest

git:
  remote: https://github.com/TheRacetrack/racetrack
  directory: sample/golang-function

resources:
    memory_min: "128Mi"
""")
    assert manifest.name == 'golang-function'
    assert manifest.git.directory == 'sample/golang-function'
    assert type(manifest.resources.memory_min) == Quantity
    assert manifest.resources.memory_min == Quantity('128Mi')


def test_directory_with_valid_manifest():
    path = tempfile.mkdtemp(prefix='job-test')
    try:
        (Path(path) / 'job.yaml').write_text("""
name: golang-function
owner_email: nobody@example.com
lang: golang:latest

git:
  remote: https://github.com/TheRacetrack/racetrack
  directory: sample/golang-function
""")
        load_validated_manifest(path)
    finally:
        shutil.rmtree(path)


def test_invalid_data_type():
    with pytest.raises(RuntimeError) as excinfo:
        validate_tmp_manifest("""
name: golang-function
owner_email: nobody@example.com
lang: golang:latest
git: its-a-string-you-moron
""")
    assert "value is not a valid dict" in str(excinfo.value)


def test_missing_required_field():
    with pytest.raises(RuntimeError) as excinfo:
        validate_tmp_manifest("""
owner_email: nobody@example.com
git:
  remote: https://github.com/TheRacetrack/racetrack
  directory: sample/golang-function
""")
    assert "name\n  field required" in str(excinfo.value)


def test_superfluous_fields():
    with pytest.raises(RuntimeError) as excinfo:
        validate_tmp_manifest("""
name: golang-function
surname: Moron
owner_email: nobody@example.com
lang: golang:latest

git:
  remote: https://github.com/TheRacetrack/racetrack
  directory: sample/golang-function
""")
    assert 'surname\n  extra fields not permitted' in str(excinfo.value)


def test_invalid_owner_email():
    with pytest.raises(RuntimeError) as excinfo:
        validate_tmp_manifest("""
name: golang-function
owner_email: moron
lang: golang:latest
git:
  remote: https://github.com/TheRacetrack/racetrack
""")
    assert '"owner_email" is not a valid email' in str(excinfo.value)


def test_missing_file():
    with pytest.raises(RuntimeError) as excinfo:
        load_validated_manifest('not-existing-path')
    assert "manifest file 'not-existing-path' doesn't exist" in str(excinfo.value)


def test_invalid_replicas():
    with pytest.raises(RuntimeError) as excinfo:
        validate_tmp_manifest("""
name: skynet
owner_email: nobody@example.com
lang: python3:latest
git:
  remote: https://github.com/TheRacetrack/racetrack
replicas: 100
""")
    assert 'replicas count out of allowed range' in str(excinfo.value)


def test_invalid_ssh_git_remote():
    with pytest.raises(RuntimeError) as excinfo:
        validate_tmp_manifest("""
name: skynet
owner_email: nobody@example.com
lang: python3:latest
git:
  remote: git@github.com:TheRacetrack/racetrack.git
""")
    assert 'git remote URL should be HTTPS' in str(excinfo.value)


def validate_tmp_manifest(content: str) -> Manifest:
    fd, path = tempfile.mkstemp(prefix='job', suffix='.yaml')
    try:
        with open(fd, 'w') as f:
            f.write(content)
        return load_validated_manifest(path)
    finally:
        os.remove(path)
