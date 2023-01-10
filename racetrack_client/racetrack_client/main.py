import argparse
import sys

from racetrack_client import __version__
from racetrack_client.client.deploy import send_deploy_request, DeploymentError
from racetrack_client.client.delete import delete_fatman
from racetrack_client.client.logs import show_runtime_logs, show_build_logs
from racetrack_client.client_config.auth import login_user_auth, logout_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.client_config.update import set_credentials, set_config_setting, set_config_url_alias
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


def main():
    parser = argparse.ArgumentParser(description='CLI client tool for deploying workloads to Racetrack')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='enable verbose mode')
    subparsers = parser.add_subparsers()

    def _print_help(_: argparse.Namespace):
        parser.print_help(sys.stderr)

    parser.set_defaults(func=_print_help)

    # racetrack deploy
    parser_deploy = subparsers.add_parser(
        'deploy', help='Send request deploying a Fatman to the Racetrack cluster')
    parser_deploy.add_argument('workdir', default='.', nargs='?', help='directory with fatman.yaml manifest')
    parser_deploy.add_argument('racetrack_url', default='', nargs='?', help='URL to Racetrack server or alias name')
    parser_deploy.add_argument('--force', action='store_true', help='overwrite existing fatman')
    parser_deploy.add_argument('--context-local', action='store_true', default=None, dest='local_context', 
        help='force building fatman from local files')
    parser_deploy.add_argument('--context-git', action='store_false', default=None, dest='local_context', 
        help='force building fatman from git repository')
    parser_deploy.set_defaults(func=_deploy)

    # racetrack validate
    parser_validate = subparsers.add_parser('validate', help='Validate Fatman manifest file')
    parser_validate.add_argument('path', default='.', nargs='?',
                                 help='path to a Fatman manifest file or to a directory with it')
    parser_validate.set_defaults(func=_validate)

    # racetrack logs
    parser_logs = subparsers.add_parser('logs', help='Show logs from fatman output')
    parser_logs.add_argument('workdir', default='.', nargs='?', help='directory with fatman.yaml manifest')
    parser_logs.add_argument('racetrack_url', default='', nargs='?', help='URL to Racetrack server or alias name')
    parser_logs.add_argument('--tail', default=20, nargs='?', type=int, help='number of recent lines to show')
    parser_logs.add_argument('--follow', '-f', action='store_true', help='follow logs output stream')
    parser_logs.set_defaults(func=_logs)

    # racetrack build-logs
    parser_build_logs = subparsers.add_parser('build-logs', help='Show build logs from fatman image building')
    parser_build_logs.add_argument('workdir', default='.', nargs='?', help='directory with fatman.yaml manifest')
    parser_build_logs.add_argument('racetrack_url', default='', nargs='?', help='URL to Racetrack server or alias name')
    parser_build_logs.add_argument('--tail', default=0, nargs='?', type=int,
                                   help='number of recent lines to show, all logs by default')
    parser_build_logs.set_defaults(func=_build_logs)

    # racetrack delete
    parser_delete = subparsers.add_parser('delete', help='Delete fatman instance')
    parser_delete.add_argument('workdir', default='.', nargs='?', help='directory with fatman.yaml manifest')
    parser_delete.add_argument('racetrack_url', default='', nargs='?', help='URL to Racetrack server or alias name')
    parser_delete.add_argument('--version', nargs='?', type=str,
                               help='fatman version to delete')
    parser_delete.set_defaults(func=_delete_fatman)

    # racetrack run-local
    parser_run = subparsers.add_parser('run-local', help='Run fatman locally')
    parser_run.add_argument('workdir', default='.', nargs='?', help='directory with fatman.yaml manifest')
    parser_run.add_argument('racetrack_url', default='', nargs='?', help='URL to Racetrack server or alias name')
    parser_run.add_argument('--port', type=int, default=None, nargs='?', help='HTTP port to run the server on')
    parser_run.add_argument('--context-local', action='store_true', default=None, dest='local_context', 
                            help='force building fatman from local files')
    parser_run.add_argument('--context-git', action='store_false', default=None, dest='local_context', 
                            help='force building fatman from git repository')
    parser_run.set_defaults(func=_run_local)

    # racetrack version
    parser_version = subparsers.add_parser('version', help='Show the version information')
    parser_version.set_defaults(func=_version)

    # racetrack config
    parser_config = subparsers.add_parser('config', help='Set local options for a Racetrack client')
    subparsers_config = parser_config.add_subparsers()

    # racetrack config show
    parser_config_show = subparsers_config.add_parser('show', help='Show racetrack config values')
    parser_config_show.set_defaults(func=_show_config)

    # racetrack config racetrack_url
    parser_config_racetrack_url = subparsers_config.add_parser(
        'racetrack_url', help='Set default Racetrack URL address')
    parser_config_racetrack_url.add_argument('setting_value', help='setting value')
    parser_config_racetrack_url.set_defaults(func=_set_config_racetrack_url)

    # racetrack config credentials
    parser_config_credentials = subparsers_config.add_parser(
        'credentials', help='Manage credentials for git repository access')
    subparsers_config_credentials = parser_config_credentials.add_subparsers()

    # racetrack config credentials set
    parser_config_credentials_set = subparsers_config_credentials.add_parser(
        'set', help='Set credentials for reading git repository')
    parser_config_credentials_set.add_argument('repo_url', help='git remote URL')
    parser_config_credentials_set.add_argument('username', help='username for git authentication')
    parser_config_credentials_set.add_argument('token_password', help='password or token for git authentication')
    parser_config_credentials_set.set_defaults(func=_set_config_credentials)

    # racetrack config alias
    parser_config_alias = subparsers_config.add_parser('alias', help='Manage aliases for Racetrack server URLs')
    subparsers_config_alias = parser_config_alias.add_subparsers()

    # racetrack config alias set
    parser_config_alias_set = subparsers_config_alias.add_parser(
        'set', help='Set up an alias for Racetrack server URL')
    parser_config_alias_set.add_argument('alias', help='short name for an environment')
    parser_config_alias_set.add_argument('racetrack_url', help='Racetrack server URL address')
    parser_config_alias_set.set_defaults(func=_set_config_url_alias)

    # racetrack login
    parser_login = subparsers.add_parser('login', help='Save user token for Racetrack server')
    parser_login.add_argument('racetrack_url', default='', nargs='?', help='URL to Racetrack server or alias name')
    parser_login.add_argument('user_token', default='', nargs='?', help='User token from RT user profile')
    parser_login.set_defaults(func=_login)

    # racetrack logout
    parser_logout = subparsers.add_parser('logout', help='Remove user token for Racetrack server')
    parser_logout.add_argument('racetrack_url', default='', nargs='?', help='URL to Racetrack server or alias name')
    parser_logout.set_defaults(func=_logout)

    # racetrack plugin
    parser_plugin = subparsers.add_parser('plugin', help='Manage Racetrack plugins')
    subparsers_plugin = parser_plugin.add_subparsers()

    # racetrack plugin install
    parser_plugin_install = subparsers_plugin.add_parser('install', help='Install a plugin to a remote Racetrack server')
    parser_plugin_install.add_argument('plugin_uri', help='location of the plugin file: local file path, URL to a remote HTTP file or repository name')
    parser_plugin_install.add_argument('racetrack_url', default='', nargs='?', help='URL to Racetrack server or alias name')
    parser_plugin_install.set_defaults(func=_install_plugin)

    # racetrack plugin uninstall
    parser_plugin_install = subparsers_plugin.add_parser('uninstall', help='Uninstall plugin from a remote Racetrack server')
    parser_plugin_install.add_argument('plugin_name', help='plugin name')
    parser_plugin_install.add_argument('plugin_version', help='plugin version')
    parser_plugin_install.add_argument('racetrack_url', default='', nargs='?', help='URL to Racetrack server or alias name')
    parser_plugin_install.set_defaults(func=_uninstall_plugin)

    # racetrack plugin list
    parser_plugin_list = subparsers_plugin.add_parser('list', help='List plugins installed on a remote Racetrack server')
    parser_plugin_list.add_argument('racetrack_url', default='', nargs='?', help='URL to Racetrack server or alias name')
    parser_plugin_list.add_argument('--job-types', action='store_true', help='list available job type versions')
    parser_plugin_list.set_defaults(func=_list_installed_plugins)

    # racetrack plugin bundle
    parser_plugin_install = subparsers_plugin.add_parser('bundle', help='Turn local plugin code into ZIP file')
    parser_plugin_install.add_argument('workdir', default='.', nargs='?', help='path to a plugin directory')
    parser_plugin_install.add_argument('--out', help='output directory where to save ZIP files')
    parser_plugin_install.add_argument('--plugin-version', help='override plugin version')
    parser_plugin_install.set_defaults(func=_plugin_bundle)

    args: argparse.Namespace = parser.parse_args()

    try:
        configure_logs(verbosity=args.verbose)
        args.func(args)
    except (DeploymentError, AuthError) as e:
        logger.error(str(e))  # no need for client's stacktrace in case of well known errors
    except Exception as e:
        log_exception(e)


def _deploy(args: argparse.Namespace):
    send_deploy_request(args.workdir, lifecycle_url=args.racetrack_url, force=args.force, local_context=args.local_context)


def _validate(args: argparse.Namespace):
    validate_and_show_manifest(args.path)


def _set_config_credentials(args: argparse.Namespace):
    set_credentials(args.repo_url, args.username, args.token_password)


def _set_config_racetrack_url(args: argparse.Namespace):
    set_config_setting('lifecycle_url', args.setting_value)


def _set_config_url_alias(args: argparse.Namespace):
    set_config_url_alias(args.alias, args.racetrack_url)


def _logs(args: argparse.Namespace):
    show_runtime_logs(args.workdir, args.racetrack_url, args.tail, args.follow)


def _build_logs(args: argparse.Namespace):
    show_build_logs(args.workdir, args.racetrack_url, args.tail)


def _delete_fatman(args: argparse.Namespace):
    delete_fatman(args.workdir, args.racetrack_url, args.version)


def _show_config(args: argparse.Namespace):
    client_config = load_client_config()
    print(datamodel_to_yaml_str(client_config))


def _version(_: argparse.Namespace):
    print(f'racetrack-client version {__version__}')


def _login(args: argparse.Namespace):
    login_user_auth(args.racetrack_url, args.user_token)


def _logout(args: argparse.Namespace):
    logout_user_auth(args.racetrack_url)


def _run_local(args: argparse.Namespace):
    run_fatman_locally(args.workdir, args.racetrack_url, local_context=args.local_context, port=args.port)


def _install_plugin(args: argparse.Namespace):
    install_plugin(args.plugin_uri, args.racetrack_url)


def _uninstall_plugin(args: argparse.Namespace):
    uninstall_plugin(args.plugin_name, args.plugin_version, args.racetrack_url)


def _list_installed_plugins(args: argparse.Namespace):
    if args.job_types:
        list_available_job_types(args.racetrack_url)
    else:
        list_installed_plugins(args.racetrack_url)


def _plugin_bundle(args: argparse.Namespace):
    bundle_plugin(args.workdir, args.out, args.plugin_version)
