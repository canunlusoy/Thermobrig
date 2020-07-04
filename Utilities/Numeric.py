from math import isnan
from typing import Union, Tuple, List

def isNumeric(value):
    return not isnan(value)


def get_rangeEndpoints(value: Union[float, int], percentUncertainty: Union[float, int]) -> Tuple:
    halfRange = value*percentUncertainty*(10**(-2))
    return (value - halfRange, value + halfRange)


def interpolate_1D(x: List[float], y: List[float], value_at: float, method: str = 'manual') -> float:

    if method == 'manual':
        assert all(len(array) == 2 for array in [x, y])
        slope = (y[1] - y[0])/(x[1] - x[0])
        return x[0] + slope*(value_at - x[0])