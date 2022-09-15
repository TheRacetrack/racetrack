from pathlib import Path
import fnmatch
from typing import Optional

DEFAULT_IGNORE_PATTERNS = {
    '*.zip',
    '.git',
    '*.pyc',
    '__pycache__',
    '.gitignore',
}


class FilenameMatcher:
    def __init__(self, patterns_file: Optional[Path] = None) -> None:
        self.patterns = set()
        self.patterns.update(DEFAULT_IGNORE_PATTERNS)

        if patterns_file:
            file_patterns = patterns_file.read_text().splitlines()
            file_patterns = list(filter(None, file_patterns))  # filter non-empty
            self.patterns.update(file_patterns)

    def match_ignore_patterns(self, relative_path: Path) -> bool:
        return any(match_file_pattern(relative_path, pattern) for pattern in self.patterns)


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

    for path_part, pattern_part in zip(path_parts, pattern_parts):
        if not fnmatch.fnmatchcase(path_part, pattern_part):
            return False
    return True
