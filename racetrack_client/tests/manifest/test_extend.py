import shutil
import tempfile
from pathlib import Path

from racetrack_client.manifest.validate import load_validated_manifest


def test_extend_base_manifest():
    path = tempfile.mkdtemp(prefix='job-test')
    try:

        (Path(path) / 'job-base.yaml').write_text("""
name: golang-function
owner_email: nobody@example.com
lang: golang:latest

git:
  remote: https://github.com/TheRacetrack/racetrack
  directory: sample/golang-function

resources:
  cpu_min: 10m
  cpu_max: 1000m
""")
        (Path(path) / 'job-overlay.yaml').write_text("""
extends: job-base.yaml

name: overlay-example

replicas: 3
resources:
  cpu_min: 100m
  memory_min: 500M
""")

        manifest = load_validated_manifest(Path(path) / 'job-overlay.yaml')
        assert manifest.extends is None
        assert manifest.name == 'overlay-example'
        assert manifest.lang == 'golang:latest'
        assert manifest.replicas == 3
        assert str(manifest.resources.memory_min) == '500M'
        assert str(manifest.resources.cpu_min) == '100m'
        assert str(manifest.resources.cpu_max) == '1000m'

    finally:
        shutil.rmtree(path)
