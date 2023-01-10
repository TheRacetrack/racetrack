import argparse
import sys

from lifecycle.server.server import run_lifecycle_server, run_lifecycle_supervisor
from racetrack_commons.auth.token import generate_service_token


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    def _print_help(_: argparse.Namespace):
        parser.print_help(sys.stderr)

    parser.set_defaults(func=_print_help)

    subparser = subparsers.add_parser('serve', help='run Lifecycle API server')
    subparser.set_defaults(func=_serve)

    subparser = subparsers.add_parser(
        'supervisor', help='run Lifecycle Supervisor process monitoring fatmen and scheduling tasks in background')
    subparser.set_defaults(func=_run_supervisor)

    subparser = subparsers.add_parser(
        'generate-auth', help='generate authentication token for internal components communication based on AUTH_KEY')
    subparser.add_argument('subject', help='subject (service) name')
    subparser.set_defaults(func=_generate_auth_token)

    args: argparse.Namespace = parser.parse_args()
    args.func(args)


def _serve(_: argparse.Namespace):
    run_lifecycle_server()


def _run_supervisor(_: argparse.Namespace):
    run_lifecycle_supervisor()


def _generate_auth_token(args: argparse.Namespace):
    generate_service_token(args.subject)
