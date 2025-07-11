import os
import sys
from typing import List, Optional, Dict

import typer

from racetrack_client import __version__
from racetrack_client.client.call import call_job
from racetrack_client.client.deploy import BuildContextMethod, send_deploy_request, DeploymentError
from racetrack_client.client.manage import JobTableColumn, move_job, delete_job, list_jobs, complete_job_name
from racetrack_client.client.logs import show_runtime_logs, show_build_logs
from racetrack_client.client.run import run_job_locally
from racetrack_client.client_config.auth import login_user_auth, logout_user_auth, get_current_auth, login_with_username
from racetrack_client.client_config.io import load_client_config
from racetrack_client.client_config.update import set_credentials, set_current_remote, set_config_url_alias
from racetrack_client.client_config.remote import get_current_remote, get_current_pub_address
from racetrack_client.plugin.bundler.bundle import bundle_plugin
from racetrack_client.plugin.install import install_plugin, list_available_job_types, list_installed_plugins, uninstall_plugin, download_installed_plugin_version
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import configure_logs
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest.validate import validate_and_show_manifest
from racetrack_client.utils.auth import AuthError
from racetrack_client.utils.datamodel import datamodel_to_yaml_str

logger = get_logger(__name__)

cli = typer.Typer(
    name='racetrack',
    help='CLI client tool for managing workloads in Racetrack',
)


def main():
    try:
        cli()
    except (DeploymentError, AuthError) as e:
        logger.error(str(e))  # no need for client's stacktrace in case of well known errors
        sys.exit(os.EX_SOFTWARE)
    except Exception as e:
        log_exception(e)
        sys.exit(os.EX_SOFTWARE)


@cli.callback()
def _startup(
    verbose: bool = typer.Option(False, '-v', '--verbose', help='enable verbose mode'),
):
    if not sys.stdout.isatty():
        configure_logs(log_level='error')
    else:
        configure_logs(log_level='debug' if verbose else 'info')

@cli.callback(invoke_without_command=True)
def default(ctx: typer.Context):
  typer.echo(ctx.get_help())

@cli.command('deploy')
def _deploy(
    workdir: str = typer.Argument(default='.', help='directory with job.yaml manifest'),
    _remote: str = typer.Argument(default=None, show_default=False, help="Racetrack server's URL or alias name (deprecated, use --remote)"),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    force: bool = typer.Option(False, '--force', help='overwrite existing job'),
    build_context: BuildContextMethod = typer.Option(BuildContextMethod.default, show_default=False, help='Force building job from local files ("local") or from git repository ("git")'),
    extra_vars: Optional[List[str]] = typer.Option(None, '-e', '--extra-vars', help='key=value pairs overriding manifest values'),
    no_cache: bool = typer.Option(False, '--no-cache', help='build without cache'),

):
    """Send request deploying a Job to the Racetrack cluster"""
    build_flags = ['--no-cache'] if no_cache else []
    send_deploy_request(workdir, lifecycle_url=remote or _remote, force=force, build_context_method=build_context,
                        extra_vars=_parse_key_value_pairs(extra_vars), build_flags=build_flags)


@cli.command('validate')
def _validate(
    path: str = typer.Argument(default='.', help='path to a Job manifest file or to a directory with it'),
    extra_vars: Optional[List[str]] = typer.Option(None, '-e', '--extra-vars', help='key=value pairs overriding manifest values'),
):
    """Validate Job manifest file"""
    validate_and_show_manifest(path, extra_vars=_parse_key_value_pairs(extra_vars))


@cli.command('logs', no_args_is_help=True)
def _logs(
    name: str = typer.Argument(..., show_default=False, help='name of the job', autocompletion=complete_job_name),
    version: str = typer.Option('latest', show_default=True, help='version of the job'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    tail: int = typer.Option(20, '--tail', help='number of recent lines to show'),
    follow: bool = typer.Option(False, '--follow', '-f', help='follow logs output stream'),
):
    """Show runtime logs from the output of a job"""
    show_runtime_logs(name, version, remote, tail, follow)


@cli.command('build-logs', no_args_is_help=True)
def _build_logs(
    name: str = typer.Argument(..., show_default=False, help='name of the job', autocompletion=complete_job_name),
    version: str = typer.Option('latest', show_default=True, help='version of the job'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    tail: int = typer.Option(0, '--tail', help='number of recent lines to show, all logs by default'),
):
    """Show build logs from job image building"""
    show_build_logs(name, version, remote, tail)


@cli.command('list')
def _list_jobs(
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    columns: List[JobTableColumn] = typer.Option([], '--column', '-c', show_default=False, help='Choose additional columns to show. "all" selects all columns.'),
):
    """List all deployed jobs"""
    list_jobs(remote, columns)


@cli.command('delete', no_args_is_help=True)
def _delete_job(
    name: str = typer.Argument(..., show_default=False, help='name of the job', autocompletion=complete_job_name),
    version: str = typer.Option(..., show_default=False, help='version of the job to delete'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
):
    """Delete job instance"""
    delete_job(name, version, remote)


@cli.command('move', no_args_is_help=True)
def _move_job(
    name: str = typer.Argument(..., show_default=False, help='name of the job', autocompletion=complete_job_name),
    version: str = typer.Option(..., show_default=False, help='version of the job to move out'),
    infrastructure: str = typer.Option(..., show_default=False, help='infrastructure target to move to'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
):
    """Move job from one infrastructure target to another"""
    move_job(remote, name, version, infrastructure)


@cli.command('run-local')
def _run_local(
    workdir: str = typer.Argument(default='.', help='directory with job.yaml manifest'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    port: int = typer.Option(default=None, show_default=False, help='HTTP port to run the server on'),
    build_context: BuildContextMethod = typer.Option(BuildContextMethod.default, show_default=False, help='Force building job from local files ("local") or from git repository ("git")'),
    extra_vars: Optional[List[str]] = typer.Option(None, '-e', '--extra-vars', help='key=value pairs overriding manifest values'),
    cmd: Optional[str] = typer.Option(default=None, show_default=False, help='Job\'s command to overwrite'),
):
    """Run job locally"""
    run_job_locally(workdir, remote, build_context_method=build_context, port=port,
                    extra_vars=_parse_key_value_pairs(extra_vars), cmd=cmd)


@cli.command('version')
def _version():
    """Show the version information"""
    print(f'racetrack-client version {__version__}')


@cli.command('login', no_args_is_help=True)
def _login(
    user_token: str = typer.Argument(default=None, show_default=False, help='Racetrack Auth Token from Racetrack\'s user profile'),
    username: str = typer.Option(default=None, show_default=False, help="Username to authenticate"),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
):
    """Save user's Racetrack Auth Token for Racetrack server"""
    if user_token:
        login_user_auth(remote, user_token)
    elif username:
        login_with_username(remote, username)
    else:
        raise RuntimeError('Use either auth token or username')


@cli.command('logout')
def _logout(
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
):
    """Remove user's Racetrack Auth Token for Racetrack server"""
    logout_user_auth(remote)


# racetrack set ...
cli_set = typer.Typer(no_args_is_help=True, help='Set local options of the Racetrack client')
cli.add_typer(cli_set, name="set")


@cli_set.command('remote', no_args_is_help=True)
def _set_remote(
    remote: str = typer.Argument(..., show_default=False, help="Racetrack server's URL or alias name"),
):
    """Set current Racetrack's remote address"""
    set_current_remote(remote)


@cli_set.command('credentials', no_args_is_help=True)
def _set_credentials(
    repo_url: str = typer.Argument(..., show_default=False, help='URL of git remote for one of your jobs'),
    username: str = typer.Argument(..., show_default=False, help='username for git authentication'),
    token_password: str = typer.Argument(..., show_default=False, help='password or token for git authentication'),
):
    """Set read-access credentials for a git repository to build images from"""
    set_credentials(repo_url, username, token_password)


@cli_set.command('alias', no_args_is_help=True)
def _set_alias(
    alias: str = typer.Argument(..., show_default=False, help='short name for an environment'),
    racetrack_url: str = typer.Argument(..., show_default=False, help='URL address of a remote Racetrack server'),
):
    """Set up an alias for Racetrack's remote URL"""
    set_config_url_alias(alias, racetrack_url)


# racetrack get ...
cli_get = typer.Typer(no_args_is_help=True, help='Read local options of the Racetrack client')
cli.add_typer(cli_get, name="get")


@cli_get.command('remote')
def _get_remote(
    quiet: bool = typer.Option(False, '--quiet', '-q', help='print only the URL address'),
):
    """Get current Racetrack's remote address (Lifecycle URL)"""
    get_current_remote(quiet)


@cli_get.command('pub')
def _get_remote(
    quiet: bool = typer.Option(False, '--quiet', '-q', help='print only the URL address'),
):
    """Get current Racetrack's Pub address"""
    get_current_pub_address(quiet)


@cli_get.command('config')
def _get_config():
    """Show all racetrack config values"""
    client_config = load_client_config()
    print(datamodel_to_yaml_str(client_config))


@cli_get.command('auth-token')
def _get_auth_token(
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
):
    """Show currently logged in auth token"""
    auth_token = get_current_auth(remote)
    print(auth_token)


# racetrack plugin ...
cli_plugin = typer.Typer(no_args_is_help=True, help='Manage Racetrack plugins')
cli.add_typer(cli_plugin, name="plugin")


@cli_plugin.command('install', no_args_is_help=True)
def _install_plugin(
    plugin_uri: str = typer.Argument(..., show_default=False, help='location of the plugin file: local file path, HTTP URL to a remote file or repository name'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    replace: bool = typer.Option(False, '--replace', help='delete the existing versions of the same plugin'),
):
    """Install a plugin to a remote Racetrack server"""
    install_plugin(plugin_uri, remote, replace=replace)


@cli_plugin.command('uninstall', no_args_is_help=True)
def _uninstall_plugin(
    plugin_name: str = typer.Argument(..., show_default=False, help='name of the plugin'),
    version: str = typer.Option(..., show_default=False, help='version of the plugin'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
):
    """Uninstall plugin from a remote Racetrack server"""
    uninstall_plugin(plugin_name, version, remote)


@cli_plugin.command('list')
def _list_installed_plugins(
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    job_types: bool = typer.Option(False, '--job-types', help='list available job type versions'),
):
    """List plugins installed on a remote Racetrack server"""
    if job_types:
        list_available_job_types(remote)
    else:
        list_installed_plugins(remote)





@cli_plugin.command('download')
def _download_installed_plugins(
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    out_dir: str = typer.Option(default=None, show_default=False, help='output directory where to save the ZIP file'),
    out_filename: str = typer.Option(default=None, show_default=False, help='filename of the output ZIP file'),
    name: str = typer.Argument(..., show_default=False, help='Name of the plugin'),
    version: str = typer.Argument(..., show_default=False, help='Version of the plugin'),
):
    """Downloads a plugin installed on a remote Racetrack server"""
    download_installed_plugin_version(remote, out_dir, name, version)


@cli_plugin.command('bundle')
def _plugin_bundle(
    workdir: str = typer.Argument(default='.', help='path to a plugin directory'),
    out: str = typer.Option(default=None, show_default=False, help='output directory where to save the ZIP file'),
    out_filename: str = typer.Option(default=None, show_default=False, help='filename of the output ZIP file'),
    plugin_version: str = typer.Option(default=None, show_default=False, help='override plugin version'),
):
    """Turn local plugin code into ZIP file"""
    bundle_plugin(workdir, out, out_filename, plugin_version)


@cli.command('call', no_args_is_help=True)
def _call_job(
    name: str = typer.Argument(..., show_default=False, help='name of the job', autocompletion=complete_job_name),
    endpoint: str = typer.Argument(..., show_default=False, help='endpoint of the job to call, eg. /api/v1/perform'),
    payload: str = typer.Argument(..., show_default=False, help='payload of the request in JSON or YAML format'),
    version: str = typer.Option('latest', show_default=True, help='version of the job'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    curl: bool = typer.Option(False, '--curl', help='generate a curl query instead of calling the job'),
):
    """Call an endpoint of a job"""
    call_job(name, version, remote, endpoint, payload, curl)


def _parse_key_value_pairs(extra_vars: Optional[List[str]]) -> Dict[str, str]:
    if not extra_vars:
        return {}
    key_values: Dict[str, str] = {}
    for var in extra_vars:
        parts = var.split('=')
        assert len(parts) == 2, f'cannot unpack key-value from "{var}"'
        key_values[parts[0]] = parts[1]
    return key_values

if __name__ == '__main__':
    main()