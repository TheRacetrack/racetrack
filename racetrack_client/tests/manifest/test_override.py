import shutil
import tempfile
from pathlib import Path

from racetrack_client.manifest.validate import load_validated_manifest


def test_override_manifest_with_extra_vars():
    path = tempfile.mkdtemp(prefix='job-test')
    try:
        (Path(path) / 'job.yaml').write_text("""
name: golang-function
owner_email: nobody@example.com
lang: golang:latest
replicas: 3
git:
  remote: https://github.com/TheRacetrack/racetrack
  directory: sample/golang-function
  branch: master
""")
        manifest_path = (Path(path) / 'job.yaml').as_posix()

        manifest = load_validated_manifest(manifest_path, extra_vars={
            'replicas': '7',
            'owner_email': 'arnold@skynet.com',
        })
        assert manifest.name == 'golang-function'
        assert manifest.replicas == 7
        assert manifest.owner_email == 'arnold@skynet.com'
        assert manifest.git.branch == 'master'

        manifest = load_validated_manifest(manifest_path, extra_vars={
            'git.branch': 'current',
        })
        assert manifest.git.branch == 'current'
        assert manifest.git.directory == 'sample/golang-function'

        manifest = load_validated_manifest(manifest_path, extra_vars={
            'git': '{"remote": "https://github"}',
        })
        assert manifest.git.remote == 'https://github'
        assert manifest.git.branch is None
        assert manifest.git.directory == '.'
        assert manifest.replicas == 3, 'other keys should remain untouched'

    finally:
        shutil.rmtree(path)
