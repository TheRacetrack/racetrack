import argparse
import sys

from fatman_wrapper.server import run_configured_entrypoint
from fatman_wrapper.config import Config
from racetrack_client.log.logs import init_logs, configure_logs
from racetrack_client.utils.config import load_config
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser('run', help='run wrapped entrypoint in a server')
    subparser.add_argument(
        'entrypoint_path', default='', nargs='?', help='path to a Python file with an entrypoint class'
    )
    subparser.add_argument('entrypoint_classname', default='', nargs='?')
    subparser.add_argument('--entrypoint_hostname', default='', help='hostname to an entrypoint HTTP server')
    subparser.add_argument('--port', type=int, default=None, nargs='?', help='HTTP port to run the server on')
    subparser.set_defaults(func=run_entrypoint)

    if len(sys.argv) > 1:
        args: argparse.Namespace = parser.parse_args()
        args.func(args)
    else:
        parser.print_help(sys.stderr)


def run_entrypoint(args: argparse.Namespace):
    """Load entrypoint class and run it embedded in a HTTP server"""
    init_logs()
    config: Config = load_config(Config)
    configure_logs(log_level=config.log_level)

    if args.port:
        config.http_port = args.port

    run_configured_entrypoint(config, args.entrypoint_path, args.entrypoint_classname, args.entrypoint_hostname)
