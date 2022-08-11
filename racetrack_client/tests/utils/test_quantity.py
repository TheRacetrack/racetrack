import pytest

from racetrack_client.utils.quantity import Quantity


def test_parse_quantity():
    assert str(Quantity('123Mi')) == '123Mi'
    assert str(Quantity('100.001')) == '100.001'
    assert str(Quantity('100000000M')) == '100000000M'


def test_convert_quantity():
    assert Quantity('1').plain_number == 1
    assert Quantity('100.001').plain_number == 100.001
    assert Quantity('123Ki').plain_number == 123 * 1024
    assert Quantity('100Mi').plain_number == 100 * 1024 * 1024
    assert Quantity('200m').plain_number == 0.2
    assert Quantity('12.234G').plain_number == 12_234_000_000


def test_invalid_quantity():
    with pytest.raises(ValueError):
        Quantity('')
    with pytest.raises(ValueError):
        Quantity('-1')
    with pytest.raises(ValueError):
        Quantity('15KB')
    with pytest.raises(ValueError):
        Quantity('1.0.0')


def test_quantity_bool():
    assert bool(Quantity('0.1')) == True
    assert bool(Quantity('0')) == False


def test_quantity_compare():
    assert Quantity('0.1') < Quantity('0.2')
    assert Quantity('0.2') > Quantity('0.1')
    assert not Quantity('0.1M') < Quantity('0.2')
    assert not Quantity('0.2') > Quantity('0.1G')
    assert Quantity('200m') == Quantity('0.2')
    assert Quantity('1Mi') == Quantity('1048.576k')
