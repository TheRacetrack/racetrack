from typing import List
import typer

from racetrack_client import __version__
from racetrack_client.client.deploy import BuildContextMethod, send_deploy_request, DeploymentError
from racetrack_client.client.manage import FatmenTableColumn, move_fatman, delete_fatman, list_fatmen
from racetrack_client.client.logs import show_runtime_logs, show_build_logs
from racetrack_client.client_config.auth import login_user_auth, logout_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.client_config.update import set_credentials, set_current_remote, set_config_url_alias
from racetrack_client.plugin.bundler.bundle import bundle_plugin
from racetrack_client.plugin.install import install_plugin, list_available_job_types, list_installed_plugins, uninstall_plugin
from racetrack_client.client.run import run_fatman_locally
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import configure_logs
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest.validate import validate_and_show_manifest
from racetrack_client.utils.auth import AuthError
from racetrack_client.utils.datamodel import datamodel_to_yaml_str

logger = get_logger(__name__)

cli = typer.Typer(
    no_args_is_help=True,
    name='racetrack',
    help='CLI client tool for managing workloads in Racetrack',
)

def main():
    try:
        cli()
    except (DeploymentError, AuthError) as e:
        logger.error(str(e))  # no need for client's stacktrace in case of well known errors
    except Exception as e:
        log_exception(e)


@cli.callback()
def _startup(
    verbose: bool = typer.Option(False, '-v', '--verbose', help='enable verbose mode'),
):
    configure_logs(verbosity=1 if verbose else 0)


@cli.command('deploy')
def _deploy(
    workdir: str = typer.Argument(default='.', help='directory with fatman.yaml manifest'),
    _remote: str = typer.Argument(default=None, show_default=False, help="Racetrack server's URL or alias name (deprecated, use --remote)"),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    force: bool = typer.Option(False, '--force', help='overwrite existing fatman'),
    build_context: BuildContextMethod = typer.Option(BuildContextMethod.default, show_default=False, help='Force building fatman from local files ("local") or from git repository ("git")'),
):
    """Send request deploying a Fatman to the Racetrack cluster"""
    send_deploy_request(workdir, lifecycle_url=remote or _remote, force=force, build_context_method=build_context)


@cli.command('validate')
def _validate(
    path: str = typer.Argument(default='.', help='path to a Fatman manifest file or to a directory with it'),
):
    """Validate Fatman manifest file"""
    validate_and_show_manifest(path)


@cli.command('logs')
def _logs(
    name: str = typer.Argument(..., show_default=False, help='name of the fatman'),
    version: str = typer.Option('latest', show_default=True, help='version of the fatman'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    tail: int = typer.Option(20, '--tail', help='number of recent lines to show'),
    follow: bool = typer.Option(False, '--follow', '-f', help='follow logs output stream'),
):
    """Show runtime logs from the output of a fatman"""
    show_runtime_logs(name, version, remote, tail, follow)


@cli.command('build-logs')
def _build_logs(
    name: str = typer.Argument(..., show_default=False, help='name of the fatman'),
    version: str = typer.Option('latest', show_default=True, help='version of the fatman'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    tail: int = typer.Option(0, '--tail', help='number of recent lines to show, all logs by default'),
):
    """Show build logs from fatman image building"""
    show_build_logs(name, version, remote, tail)


@cli.command('list')
def _list_fatmen(
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    columns: List[FatmenTableColumn] = typer.Option([], '--column', '-c', show_default=False, help='Choose additional columns to show. "all" selects all columns.'),
):
    """List all deployed fatmen"""
    list_fatmen(remote, columns)


@cli.command('delete')
def _delete_fatman(
    name: str = typer.Argument(..., show_default=False, help='name of the fatman'),
    version: str = typer.Option(..., show_default=False, help='version of the fatman to delete'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
):
    """Delete fatman instance"""
    delete_fatman(name, version, remote)


@cli.command('move')
def _move_fatman(
    name: str = typer.Argument(..., show_default=False, help='name of the fatman'),
    version: str = typer.Option(..., show_default=False, help='version of the fatman to move out'),
    infrastructure: str = typer.Option(..., show_default=False, help='infrastructure target to move to'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
):
    """Move fatman from one infrastructure target to another"""
    move_fatman(remote, name, version, infrastructure)


@cli.command('run-local')
def _run_local(
    workdir: str = typer.Argument(default='.', help='directory with fatman.yaml manifest'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
    port: int = typer.Option(default=None, show_default=False, help='HTTP port to run the server on'),
    build_context: BuildContextMethod = typer.Option(BuildContextMethod.default, show_default=False, help='Force building fatman from local files ("local") or from git repository ("git")'),
):
    """Run fatman locally"""
    run_fatman_locally(workdir, remote, build_context_method=build_context, port=port)


@cli.command('version')
def _version():
    """Show the version information"""
    print(f'racetrack-client version {__version__}')


@cli.command('login')
def _login(
    remote: str = typer.Argument(..., show_default=False, help="Racetrack server's URL or alias name"),
    user_token: str = typer.Argument(..., show_default=False, help='Racetrack Auth Token from Racetrack\'s user profile'),
):
    """Save user's Racetrack Auth Token for Racetrack server"""
    login_user_auth(remote, user_token)


@cli.command('logout')
def _logout(
    remote: str = typer.Argument(..., show_default=False, help="Racetrack server's URL or alias name"),
):
    """Remove user's Racetrack Auth Token for Racetrack server"""
    logout_user_auth(remote)


# racetrack config ...
cli_config = typer.Typer(no_args_is_help=True, help='Manage local options for a Racetrack client')
cli.add_typer(cli_config, name="config")


@cli_config.command('remote')
def _set_config_remote(
    remote: str = typer.Argument('', show_default=False, help="Racetrack server's URL or alias name"),
):
    """Set current Racetrack remote address"""
    set_current_remote(remote)


@cli_config.command('racetrack_url', deprecated=True)
def _set_config_racetrack_url(
    remote: str = typer.Argument(..., show_default=False, help="Racetrack server's URL or alias name"),
):
    """Set current Racetrack remote address"""
    set_current_remote(remote)


@cli_config.command('show')
def _show_config():
    """Show racetrack config values"""
    client_config = load_client_config()
    print(datamodel_to_yaml_str(client_config))


# racetrack config credentials ...
cli_config_credentials = typer.Typer(no_args_is_help=True, help='Manage credentials for git repository access')
cli_config.add_typer(cli_config_credentials, name="credentials")


@cli_config_credentials.command('set')
def _set_config_credentials(
    repo_url: str = typer.Argument(..., show_default=False, help='URL of git remote for one of your fatmen'),
    username: str = typer.Argument(..., show_default=False, help='username for git authentication'),
    token_password: str = typer.Argument(..., show_default=False, help='password or token for git authentication'),
):
    """Set credentials for reading git repository"""
    set_credentials(repo_url, username, token_password)


# racetrack config alias ...
cli_config_alias = typer.Typer(no_args_is_help=True, help='Manage aliases for Racetrack server URLs')
cli_config.add_typer(cli_config_alias, name="alias")


@cli_config_alias.command('set')
def _set_config_url_alias(
    alias: str = typer.Argument(..., show_default=False, help='short name for an environment'),
    racetrack_url: str = typer.Argument(..., show_default=False, help='URL address of a remote Racetrack server'),
):
    """Set up an alias for Racetrack remote URL"""
    set_config_url_alias(alias, racetrack_url)


# racetrack plugin ...
cli_plugin = typer.Typer(no_args_is_help=True, help='Manage Racetrack plugins')
cli.add_typer(cli_plugin, name="plugin")


@cli_plugin.command('install')
def _install_plugin(
    plugin_uri: str = typer.Argument(..., show_default=False, help='location of the plugin file: local file path, HTTP URL to a remote file or repository name'),
    remote: str = typer.Option(default=None, show_default=False, help="Racetrack server's URL or alias name"),
):
    """Install a plugin to a remote Racetrack server"""
    install_plugin(plugin_uri, remote)


@cli_plugin.command('uninstall')
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


@cli_plugin.command('bundle')
def _plugin_bundle(
    workdir: str = typer.Argument(default='.', help='path to a plugin directory'),
    out: str = typer.Option(default=None, show_default=False, help='output directory where to save the ZIP file'),
    plugin_version: str = typer.Option(default=None, show_default=False, help='override plugin version'),
):
    """Turn local plugin code into ZIP file"""
    bundle_plugin(workdir, out, plugin_version)
