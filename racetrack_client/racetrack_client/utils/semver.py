import re
from typing import Callable, List, Optional, TypeVar


T = TypeVar("T")


class SemanticVersion:
    """
    Version numbering adhering to Semantic Versioning Specification (SemVer)
    It should match `MAJOR.MINOR.PATCH[LABEL]` format, eg.:
    - 1.2.3
    - 10.0.1-alpha
    - 0.0.0-dev
    """

    version_pattern = re.compile(r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?P<label>.*)')

    def __init__ (self, vstring):
        match = self.version_pattern.fullmatch(vstring)
        if not match:
            raise ValueError(f"Version '{vstring}' doesn't match SemVer format 'X.Y.Z[-label]'")
        self.major = int(match.group('major'))
        self.minor = int(match.group('minor'))
        self.patch = int(match.group('patch'))
        self.label = match.group('label')

    @staticmethod
    def find_latest_stable(objects: List[T], key: Callable[[T], str]) -> Optional[T]:
        """
        Find object with the latest stable version - highest version disregarding versions with labels, eg "-dev"
        :param objects: List of objects to compare
        :param key: Callable to extract version from an object
        :return: Object from a list having the latest stable version
        """
        versions_objects = {SemanticVersion(key(obj)): obj for obj in objects}
        # filter stable versions
        versions_objects = {version: obj for version, obj in versions_objects.items()
                            if not version.label}
        if not versions_objects:
            return None

        latest_version = max(versions_objects.keys())
        return versions_objects[latest_version]

    @staticmethod
    def find_latest_wildcard(pattern: 'SemanticVersionPattern', objects: List[T], key: Callable[[T], str]) -> Optional[T]:
        """
        Find object with the latest (highest), stable (non-dev) version matching pattern
        :param pattern: version pattern containing "x" wildcards, eg. "1.2.x", "2.x"
        :param objects: List of objects to compare
        :param key: Callable to extract version from an object
        :return: Object from a list having the latest version matching pattern
        """
        versions_objects = {SemanticVersion(key(obj)): obj for obj in objects}
        # filter stable versions matching pattern
        versions_objects = {version: obj for version, obj in versions_objects.items()
                            if not version.label and pattern.matches(version)}
        if not versions_objects:
            return None

        latest_version = max(versions_objects.keys())
        return versions_objects[latest_version]


    def __str__ (self):
        return f'{self.major}.{self.minor}.{self.patch}{self.label}'

    def _compare(self, other) -> int:
        """
        Returns zero if objects are considered "equal",
        negative if self is less than other, otherwise return positive.
        """
        if isinstance(other, str):
            other = SemanticVersion(other)

        if self.major != other.major:
            return self.major - other.major
        if self.minor != other.minor:
            return self.minor - other.minor
        if self.patch != other.patch:
            return self.patch - other.patch

        return self._compare_labels(self.label, other.label)

    def __eq__(self, other):
        if type(other) is type(self):
            return self._compare(other) == 0
        else:
            return False

    def __lt__(self, other):
        return self._compare(other) < 0

    def __le__(self, other):
        return self._compare(other) <= 0

    def __gt__(self, other):
        return self._compare(other) > 0

    def __ge__(self, other):
        return self._compare(other) >= 0

    @staticmethod
    def _compare_labels(label1: str, label2: str) -> int:
        if label1 == label2:
            return 0
        # According to Semver, pre-release version has lower precedence than a normal version
        # Example: 1.0.0-alpha < 1.0.0.
        if not label2:
            return -1
        if not label1:
            return 1

        if label1 < label2:
            return -1
        else:
            return 1
    
    def __members(self):
        return (self.major, self.minor, self.patch, self.label)

    def __hash__(self):
        return hash(self.__members())


class SemanticVersionPattern:
    valid_pattern_regex = re.compile(r'(\d+|x)(\.(\d+|x))*')  # 1.2.x or 1.x or 1.x.x

    def __init__(self, pattern: str) -> None:
        """
        :param pattern: version pattern containing "x" wildcards, eg. "1.2.x", "2.x"
        """
        match = self.valid_pattern_regex.fullmatch(pattern)
        if not match:
            raise ValueError(f"Version pattern '{pattern}' is invalid, should be '1.x' or '1.2.x'")
        if 'x' not in pattern:
            raise ValueError(f"Version pattern '{pattern}' doesn't contain 'x' wildcard")

        self.regex_pattern = re.compile(pattern.replace('.', r'\.').replace('x', r'.+'))

    def matches(self, version: SemanticVersion) -> bool:
        return self.regex_pattern.fullmatch(str(version)) is not None

    @staticmethod
    def is_wildcard_pattern(pattern: str) -> bool:
        match = SemanticVersionPattern.valid_pattern_regex.fullmatch(pattern)
        if not match:
            return False
        return 'x' in pattern
