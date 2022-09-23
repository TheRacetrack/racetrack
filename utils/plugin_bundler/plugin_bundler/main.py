#!/usr/bin/env python3
import sys
import argparse

from racetrack_client.log.logs import configure_logs, get_logger

from plugin_bundler.bundle import bundle_plugin

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    def _print_help(_: argparse.Namespace):
        parser.print_help(sys.stderr)

    parser.set_defaults(func=_print_help)
    parser.add_argument('-v', '--verbose', action='count', default=0, help='enable verbose mode')

    subparser = subparsers.add_parser('bundle', help='Bundle plugin into ZIP files')
    subparser.add_argument('workdir', default='.', nargs='?', help='path to a plugin directory')
    subparser.set_defaults(func=_bundle)

    args: argparse.Namespace = parser.parse_args()

    verbose = args.verbose > 0
    configure_logs(verbosity=verbose)

    args.func(args)


def _bundle(args: argparse.Namespace):
    bundle_plugin(args.workdir)


if __name__ == '__main__':
    main()
