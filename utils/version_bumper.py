#!/usr/bin/env python3
import argparse
import os
import re
import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

"""
Supports following cases:

1. Master version x.y.z needs to be bumped to x.y.z when preparing for official release:  
    
    git checkout cluster-test
    git merge master
    # version = x.y.z
     
    version_bumper.py
    # version = x.y.z+1

    version_bumper.py --part=minor
    # version = x.y+1.0
    
    version_bumper.py --part=major
    # version = x+1.0.0 

2. Master version x.y.z needs to be bumped to x.y.z-mr-1 when making dev release from feature branch:

    git co 123-my-branch
    # version = x.y.z 
    
    version_bumper.py --mr 123
    # version = x.y.z-123-1

 And then another call should just bump the dev-version:
    version_bumper.py --mr 123
    # version = x.y.z-123-2 


"""


@dataclass
class Version:
    major: int
    minor: int
    patch: int
    mr: int   # merge request id
    dev: int  # sequentially increasing number

    def __str__(self):
        mr = f"-{self.mr}" if self.mr > 0 else ''
        dev = f"-{self.dev}" if self.dev > 0 else ''
        return f'{self.major}.{self.minor}.{self.patch}{mr}{dev}'

    def bump(self, part: str):
        self.__dict__[part] += 1
        if part == 'major':
            self.minor = self.patch = 0
        if part == 'minor':
            self.patch = 0

    def clone(self) -> 'Version':
        return dataclasses.replace(self)


def read_current_version(filepath: Path) -> Version:
    for line in filepath.read_text().splitlines():
        ver = parse_makefile_version(line)
        if ver is not None:
            return ver
    raise RuntimeError('version could not be parsed from ' + str(filepath))


# match X.Y.Z or X.Y.Z-W
# broken down at https://regex101.com/r/IAccOs/3
makefile_pattern = re.compile(r'TAG\s*\?=\s*?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)[\-\.]?(?P<details>[\-\w]+)?')
version_pattern = re.compile(r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)[\-\.]?(?P<details>[\-\w]+)?')


def parse_makefile_version(line: str) -> Optional[Version]:
    match = makefile_pattern.match(line)
    if not match:
        return None
    ver = Version(major=int(match.group('major')),
                  minor=int(match.group('minor')),
                  patch=int(match.group('patch')),
                  mr=0,
                  dev=0)
    details = match.group('details')
    if details is not None:
        parse_details(details, ver)
    return ver


def parse_version(line: str) -> Optional[Version]:
    match = version_pattern.fullmatch(line)
    if not match:
        return None
    ver = Version(major=int(match.group('major')),
                  minor=int(match.group('minor')),
                  patch=int(match.group('patch')),
                  mr=0,
                  dev=0)
    details = match.group('details')
    if details is not None:
        parse_details(details, ver)
    return ver


# match X-Y
# broken down at https://regex101.com/r/jtlQ54/3
details_regex = r'(?P<mr>\d+)[\-](?P<dev>\d+)'
details_pattern = re.compile(details_regex)


def parse_details(details: str, ver: Version):
    details_match = details_pattern.match(details)
    if details_match:
        ver.mr = int(details_match.group('mr'))
        ver.dev = int(details_match.group('dev'))


def replace_in_files(curr_ver: Version, new_ver: Version, files: List[Path]):
    for file in files:
        replace_in_file(file, curr_ver, new_ver)


def replace_in_file(filepath: Path, curr_ver: Version, new_ver: Version):
    content = filepath.read_text()
    new_content = content.replace(str(curr_ver), str(new_ver))
    if content != new_content:
        filepath.write_text(new_content)
        print(f'Version bumped {curr_ver} -> {new_ver} in {filepath}')
    else:
        raise RuntimeError(f'Version "{curr_ver}" not found in {filepath}')


def project_root() -> Path:
    """Return Racetrack root dir"""
    return Path(os.path.abspath(__file__)).parent.parent.absolute()


def bump_version_in_files(version_path: Path, _args, files: List[Path], prod_files: List[Path]):
    orig_version = read_current_version(version_path)

    if _args.current:
        print(orig_version)
        return

    new_version = orig_version.clone()
    if _args.mr and int(_args.mr) != 0:
        new_version.mr = int(_args.mr)
    if _args.exact:
        exact_version = parse_version(_args.exact)
        assert exact_version is not None
        new_version = exact_version

    if new_version.mr != 0:
        new_version.bump('dev')
    elif _args.exact:
        files += prod_files
    else:
        new_version.bump(_args.part)
        files += prod_files
    if new_version == orig_version:
        print(f'Version {new_version} is already set')
        return
    replace_in_files(orig_version, new_version, files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--current', action='store_true', help='print current version')
    parser.add_argument('--mr', help='set merge request number')
    parser.add_argument('--exact', help='set version to exact value')
    parser.add_argument('--part', help='defines which part to bump: major, minor, patch, dev', default="patch")

    files_with_version = [
        project_root() / 'Makefile',
    ]
    # files bumped in official (non-dev) releases only
    prod_files_with_version = [
        project_root() / 'racetrack_client/racetrack_client/__init__.py',
    ]

    args = parser.parse_args()
    path = project_root() / 'Makefile'
    bump_version_in_files(path, args, files_with_version, prod_files_with_version)

