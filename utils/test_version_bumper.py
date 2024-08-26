import tempfile
import shutil
from pathlib import Path

from version_bumper import parse_makefile_version, replace_in_files, read_current_version, Version, bump_version_in_files


def test_basic():
    ver: Version = parse_makefile_version('TAG?=1.2.16')
    assert ver
    assert ver.major == 1
    assert ver.minor == 2
    assert ver.patch == 16
    assert ver.mr == 0
    assert ver.dev == 0
    assert str(ver) == '1.2.16'


def test_whitespace():
    ver: Version = parse_makefile_version('TAG  ?=  1.2.16  ')
    assert ver
    assert ver.major == 1
    assert ver.minor == 2
    assert ver.patch == 16
    assert ver.mr == 0
    assert ver.dev == 0
    assert str(ver) == '1.2.16'


def test_mr_dev():
    ver: Version = parse_makefile_version('TAG ?= 1.2.16-123-456')
    assert ver
    assert ver.major == 1
    assert ver.minor == 2
    assert ver.patch == 16
    assert ver.mr == 123
    assert ver.dev == 456
    assert str(ver) == '1.2.16-123-456'


def test_bump_major():
    ver: Version = parse_makefile_version('TAG ?= 1.2.16-123-456')
    assert ver.major == 1
    ver.bump("major")

    assert ver.major == 2
    assert ver.minor == 0
    assert ver.patch == 0
    assert ver.mr == 123
    assert ver.dev == 456
    assert str(ver) == '2.0.0-123-456'


def test_bump_minor():
    ver: Version = parse_makefile_version('TAG ?= 1.2.16-123-456')
    assert ver.minor == 2
    ver.bump("minor")

    assert ver.major == 1
    assert ver.minor == 3
    assert ver.patch == 0
    assert ver.mr == 123
    assert ver.dev == 456
    assert str(ver) == '1.3.0-123-456'


def test_bump_patch():
    ver: Version = parse_makefile_version('TAG ?= 1.2.16-123-456')
    assert ver.patch == 16
    ver.bump("patch")

    assert ver.major == 1
    assert ver.minor == 2
    assert ver.patch == 17
    assert ver.mr == 123
    assert ver.dev == 456
    assert str(ver) == '1.2.17-123-456'


def test_bump_dev():
    ver: Version = parse_makefile_version('TAG ?= 1.2.16-123-456')
    assert ver.minor == 2
    ver.bump("dev")

    assert ver.major == 1
    assert ver.minor == 2
    assert ver.patch == 16
    assert ver.mr == 123
    assert ver.dev == 457
    assert str(ver) == '1.2.16-123-457'


def test_file_replace_makefile():
    path = tempfile.mkdtemp(prefix='versions-test')
    try:
        makefile = (Path(path) / 'Makefile')
        makefile.write_text("""
SHELL=/bin/bash
# docker tag of images
TAG ?= 2.31.1
""")
        cur_ver: Version = read_current_version(makefile)
        assert str(cur_ver) == "2.31.1"

        new_ver = cur_ver.clone()
        new_ver.bump("patch")
        replace_in_files(cur_ver, new_ver, [makefile])

        changed: Version = read_current_version(makefile)
        assert str(changed) == "2.31.2"
    finally:
        shutil.rmtree(path)


def test_file_replace_k8s():
    path = tempfile.mkdtemp(prefix='versions-test')
    try:
        makefile = (Path(path) / 'Makefile')
        makefile.write_text("""
SHELL=/bin/bash
# docker tag of images
TAG ?= 1.2.16
""")
        cur_ver: Version = read_current_version(makefile)
        new_ver = cur_ver.clone()
        new_ver.bump("patch")

        lifecycle = (Path(path) / 'lifecycle.yaml')
        lc_pre = """
            image: ghcr.io/theracetrack/racetrack/lifecycle:1.2.16
        """
        lifecycle.write_text(lc_pre)

        replace_in_files(cur_ver, new_ver, [lifecycle])

        lc_expected = """
            image: ghcr.io/theracetrack/racetrack/lifecycle:1.2.17
        """
        assert lifecycle.read_text() == lc_expected

    finally:
        shutil.rmtree(path)


def test_script():
    path = tempfile.mkdtemp(prefix='versions-test')
    try:
        makefile = (Path(path) / 'Makefile')
        makefile.write_text("""
# docker TAG of images
TAG?=1.2.1
""")
        from types import SimpleNamespace
        args = SimpleNamespace()
        args.mr = 87
        args.current = None
        args.part = 'patch'

        lifecycle = (Path(path) / 'lifecycle.yaml')
        lc_pre = """
            image: ghcr.io/theracetrack/racetrack/lifecycle:1.2.1
        """
        lifecycle.write_text(lc_pre)

        bump_version_in_files(makefile, args, [makefile, lifecycle], [])
        lc_expected = """
            image: ghcr.io/theracetrack/racetrack/lifecycle:1.2.1-87-1
        """
        assert lifecycle.read_text() == lc_expected

        args.mr = 0
        bump_version_in_files(makefile, args, [makefile, lifecycle], [])
        lc_expected = """
            image: ghcr.io/theracetrack/racetrack/lifecycle:1.2.1-87-2
        """
        assert lifecycle.read_text() == lc_expected

    finally:
        shutil.rmtree(path)
