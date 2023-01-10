from pathlib import Path
import fnmatch
from typing import List

DEFAULT_IGNORE_PATTERNS = [
    '*.zip',
    '.git',
    '*.pyc',
    '__pycache__',
    '.gitignore',
    '/.racetrackignore',
    '/plugin-manifest.yaml',
]


class FilenameMatcher:
    """
    A matcher checking if the file path matches one of the given wildcard patterns.
    This is especially useful for checking if the file should be ignored due to gitignore-alike patterns.
    Filename patterns should be given in Unix shell-style wildcards syntax
    (very similar to well-known .gitignore syntax).

    Besides, if you want to include or exclude specific files,
    you can prepend the patterns with "+" (to include) or "-" (to exclude).
    Rules are evaluated in order of occurrence. For instance:
        -whole_dir
        +whole_dir/but_this
        -whole_dir/but_this/without_that
    """
    def __init__(self, file_patterns: List[str] = None, apply_defaults: bool = True) -> None:
        self.patterns: List[str] = []

        if file_patterns:
            file_patterns = list(filter(None, file_patterns))  # filter non-empty
            self.patterns.extend(file_patterns)

        if apply_defaults:
            self.patterns.extend(DEFAULT_IGNORE_PATTERNS)

    def match_path(self, relative_path: Path) -> bool:
        """Check whether the file path should be included (True) or excluded (False)"""
        result = True

        for pattern in self.patterns:

            # result that should be applied if a file matches the pattern
            pattern_result = False
            if pattern.startswith('-'):
                pattern = pattern[1:]
            elif pattern.startswith('+'):
                pattern_result = True
                pattern = pattern[1:]

            if match_file_pattern(relative_path, pattern):
                result = pattern_result

        return result


def match_file_pattern(relative_path: Path, pattern: str) -> bool:
    if pattern.startswith('/'):
        return _match_file_pattern_beginning(relative_path, pattern[1:])

    pattern_parts = Path(pattern).parts
    path_parts = relative_path.parts

    if len(pattern_parts) == 1:
        for path_part in path_parts:
            if fnmatch.fnmatchcase(path_part, pattern):
                return True

    if len(pattern_parts) > 1:
        if len(path_parts) < len(pattern_parts):
            return False
        for path_part, pattern_part in zip(reversed(path_parts), reversed(pattern_parts)):
            if not fnmatch.fnmatchcase(path_part, pattern_part):
                return False
        return True
    
    return False


def _match_file_pattern_beginning(relative_path: Path, pattern: str) -> bool:
    path_parts = relative_path.parts
    pattern_parts = Path(pattern).parts

    if len(path_parts) < len(pattern_parts):
            return False

    for path_part, pattern_part in zip(path_parts, pattern_parts):
        if not fnmatch.fnmatchcase(path_part, pattern_part):
            return False

    return True
