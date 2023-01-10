
from racetrack_client import main
import sys


def test_commons_imported():
    assert 'racetrack_commons' not in sys.modules, 'racetrack_commons has been imported in client - forbidden'


def test_lifecycle_not_imported():
    assert 'lifecycle' not in sys.modules, 'lifecycle has been imported in client - forbidden'
