from racetrack_client.main import cli
import typer.testing

vaild_job_yaml_text = """
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

def test_valid_manifest_direct_pipe_to_deploy():
    # Test if piping input works
    runner = typer.testing.CliRunner()
    result = runner.invoke(cli, ['deploy'], input=vaild_job_yaml_text)
    assert result.exit_code != 0, "Command should fail since there's no real workdir"
    assert "deployment error" in str(result.exception).lower(), "Unexpected error type"


invaild_job_yaml_text = r"""
 __________________
< invalid manifest >
 ------------------
        \\   ^__^
         \\  (oo)\\_______
             (__)\\       )\\/\\
                ||----w |
                ||     ||
"""

def test_invalid_manifest_direct_pipe_to_deploy():
    # Test if piping input works
    runner = typer.testing.CliRunner()
    result = runner.invoke(cli, ['deploy'], input=invaild_job_yaml_text)
    print( str(result.exception))
    assert result.exit_code != 0, "Command should fail since the manifest is invalid"
    assert "'str' object has no attribute 'get'" in str(result.exception).lower(), "Unexpected error type"

