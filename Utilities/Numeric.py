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
        return y[0] + slope*(value_at - x[0])


def isApproximatelyEqual(value1: float, value2: float, max_percentDifference: float) -> bool:
    percentDifference = 100 * (abs(value1 - value2) / ((value1 + value2) / 2))
    return percentDifference <= max_percentDifference


def isWithin(value_1: float, within_value: float, within_unit: str, value_2: float):
    if within_unit == 'units':
        return abs(value_1 - value_2) <= within_value
    elif within_unit == '%':
        return 100 * abs(value_1 - value_2)/((value_1 + value_2) / 2) <= within_value
    else:
        return None
