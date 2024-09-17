import backoff
from contextlib import contextmanager
import os


@backoff.on_exception(backoff.expo, AssertionError, factor=0.1, max_time=10, jitter=None)
def wait_until_equal(collection1, collection2, err_message: str):
    assert collection1 == collection2, err_message


@contextmanager
def change_workdir(path: str):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)
