from racetrack_client.main import cli
import typer.testing


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
    assert result.exit_code != 0, "Command should fail since the manifest is invalid"
    error_message = str(result.exception).lower()
    assert "'str' object has no attribute 'get'" in error_message or "'nonetype' object is not iterable" in error_message, "Unexpected error type"
