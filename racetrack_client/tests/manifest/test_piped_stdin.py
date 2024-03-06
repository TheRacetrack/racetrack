from racetrack_client.main import cli
import typer.testing

job_yaml_text = """
name: job
owner_email: sample@example.com
lang: python3:latest
version: 0.2.0

git:
  remote: https://github.com/anders314159/tiny_job
  branch: main
  directory: job

jobtype_extra:
  entrypoint_path: 'adder.py'
  entrypoint_class: 'AdderModel'
"""

def test_direct_pipe_to_deploy():
    # Test if piping input works
    runner = typer.testing.CliRunner()
    result = runner.invoke(cli, ['deploy', '--build-context=git'], input=job_yaml_text)
    assert result.exit_code == 0, "Command execution failed"
