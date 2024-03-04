import os
import tempfile
import typer.testing
from unittest.mock import patch
from racetrack_client.main import cli
from racetrack_client.manifest.validate import load_validated_manifest

job_yaml_text = """
name: job
owner_email: sample@example.com
lang: python3:latest
version: 0.1.0

git:
  remote: https://github.com/anders314159/tiny_job
  branch: main
  directory: job

jobtype_extra:
  entrypoint_path: 'adder.py'
  entrypoint_class: 'AdderModel'
"""

@patch('racetrack_client.main.send_deploy_request') # Mock the deploy request
def test_direct_pipe_to_deploy(mock_send_deploy):
    # Validate that the manifest, job_yaml_text, is actually correct.
    with tempfile.NamedTemporaryFile(mode='w+', dir=os.getcwd(), delete=True) as tmp_file:
        tmp_file.write(job_yaml_text)
        tmp_file.flush()
        load_validated_manifest(tmp_file.name, {})

    # Test if piping input works - note we skip `send_deploy_request` entirely
    runner = typer.testing.CliRunner()
    result = runner.invoke(cli, ['deploy'], input=job_yaml_text)
    print("result.stdout")
    print(result.stdout)
    assert result.exit_code == 0, "Command execution failed"

job_yaml_text_fail = """
This should not be a valid manifest - load_validated_manifest should raise an exception
"""

@patch('racetrack_client.main.send_deploy_request') # Mock the deploy request
def test_sanity_check(mock_send_deploy):
    # Validate that the manifest, job_yaml_text, is actually correct.
    with tempfile.NamedTemporaryFile(mode='w+', dir=os.getcwd(), delete=True) as tmp_file:
        tmp_file.write(job_yaml_text_fail)
        tmp_file.flush()
        try:
            load_validated_manifest(tmp_file.name, {})
            assert False, "Fails if no exception is raised."
        except Exception as e: # Don't care about the exception type, but the above should raise an exception
            print(e)
            assert True, "This should not be a valid manifest"
