from pathlib import Path
from plugin_bundler.filename_matcher import match_file_pattern, FilenameMatcher


def test_match_file_patterns():
    assert match_file_pattern(Path('dir/folder/plugin-1.1.0.zip'), '*.zip')
    assert not match_file_pattern(Path('dir/f.zipper.txt'), '*.zip')

    assert match_file_pattern(Path('dir/folder/.git'), '.git')
    assert match_file_pattern(Path('.git'), '.git')
    assert match_file_pattern(Path('.git/file'), '.git')

    assert match_file_pattern(Path('dir/__pycache__'), '__pycache__')
    assert match_file_pattern(Path('__pycache__'), '__pycache__')

    assert match_file_pattern(Path('venv'), '/venv')
    assert match_file_pattern(Path('venv/internals'), '/venv')
    assert not match_file_pattern(Path('folder/venv'), '/venv')
    assert match_file_pattern(Path('venv/x/internals'), '/venv/x')

    assert match_file_pattern(Path('logs/out.txt'), 'logs/out.txt')
    assert not match_file_pattern(Path('out.txt'), 'logs/out.txt')
    assert match_file_pattern(Path('folder/logs/out.txt'), 'logs/out.txt')

    assert not match_file_pattern(Path('somewhere/over'), '/somewhere/over/the_rainbow')


def test_exclude_and_include():
    matcher = FilenameMatcher([
        '-/whole_dir',
        '+/whole_dir/but_this',
        '-/whole_dir/but_this/without_that',
        '-*.zip',
    ])
    assert matcher.match_path(Path('plugin-1.1.0.txt'))
    assert matcher.match_path(Path('elsewhere/plugin-1.1.0.txt'))
    assert not matcher.match_path(Path('elsewhere/plugin-1.1.0.zip'))
    assert not matcher.match_path(Path('whole_dir'))
    assert not matcher.match_path(Path('whole_dir/plugin-1.1.0.txt'))
    assert matcher.match_path(Path('whole_dir/but_this'))
    assert matcher.match_path(Path('whole_dir/but_this/code/plugin-1.1.0.txt'))
    assert not matcher.match_path(Path('whole_dir/but_this/without_that'))
    assert not matcher.match_path(Path('whole_dir/but_this/without_that/plugin-1.1.0.txt'))
