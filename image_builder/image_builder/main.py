import argparse
import sys

from image_builder.api import run_api_server


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser('serve', help='run API server')
    subparser.set_defaults(func=_serve)

    if len(sys.argv) == 0:
        parser.print_help(sys.stderr)
    else:
        args: argparse.Namespace = parser.parse_args()
        args.func(args)


def _serve(_: argparse.Namespace):
    run_api_server()
