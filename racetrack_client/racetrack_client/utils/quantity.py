from functools import total_ordering
import re


@total_ordering
class Quantity:
    _suffix_multipliers = {
        'E': 1e18,
        'P': 1e15,
        'T': 1e12,
        'G': 1e9,
        'M': 1e6,
        'k': 1e3,
        '': 1,
        'm': 1e-3,
        'u': 1e-6,
        'n': 1e-9,
        'p': 1e-12,
        'Ei': 1024**6,
        'Pi': 1024**5,
        'Ti': 1024**4,
        'Gi': 1024**3,
        'Mi': 1024**2,
        'Ki': 1024,
    }

    def __init__(self, quantity_str: str):
        """
        Data type for representing fixed-point number with quantity suffixes
        Useful for measuring memory amount in bytes, or CPU consumption.

        :param quantity_str: plain integer, or fixed-point number
        using one of the quantity suffixes T, G, M, k, m, etc.
        You can also use the power-of-two equivalents: Ti, Gi, Mi, Ki
        For instance: 128974848, 129M, 128974848000m, 123Mi, 0.129G
        """
        self.quantity_str: str = quantity_str

        match = re.fullmatch(r'(?P<number>\d+(\.\d+)?)(?P<suffix>.*)', quantity_str)
        if match is None:
            raise ValueError(f'invalid quantity format: {quantity_str}, use "<number><suffix>"')

        self.base_number: float = float(match.group('number'))
        self.suffix: str = match.group('suffix')

        if not self.suffix in self._suffix_multipliers:
            raise ValueError(f'invalid suffix: {self.suffix}, use one of {self._suffix_multipliers.keys()}')

    def __str__(self) -> str:
        return self.quantity_str

    def __repr__(self) -> str:
        return self.__str__()
    
    def __bool__(self) -> bool:
        return self.base_number > 0

    def __eq__(self, other) -> bool:
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.plain_number == other.plain_number

    def __lt__(self, other) -> bool:
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.plain_number < other.plain_number

    def __to_json__(self) -> str:
        return self.quantity_str

    def __truediv__(self, other) -> 'Quantity':
        if isinstance(other, (int, float)):
            result_base_number = self.base_number / other
            if result_base_number.is_integer():
                result_base_number = int(result_base_number)
            return Quantity(f'{result_base_number}{self.suffix}')
        else:
            raise NotImplementedError()

    @property
    def plain_number(self) -> float:
        """Convert quantity to a plain number without any suffixes"""
        return self.base_number * self._suffix_multipliers[self.suffix]
