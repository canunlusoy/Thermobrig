from math import isnan
from typing import Union, Tuple, List, Dict
from bisect import bisect_left, bisect_right
from time import time

from Utilities.Exceptions import NeedsExtrapolationError

def isNumeric(value):
    return not isnan(value)


def get_surroundingValues(dataList: List, value: Union[float, int]) -> Tuple:

    dataList = sorted(dataList)
    valueBelow = dataList[bisect_left(dataList, value) - 1]
    if valueBelow > value:
        raise NeedsExtrapolationError('valueBelow could not be found')

    try:
        valueAbove = dataList[bisect_right(dataList, value)]
    except IndexError:
        raise NeedsExtrapolationError('valueAbove could not be found.')

    assert valueBelow <= value <= valueAbove
    return valueBelow, valueAbove


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


def get_doubleInterpolationRectangle(pairs: List[Tuple], refPropt1_name, refPropt1_queryValue, refPropt2_name, refPropt2_queryValue):

    # refPropt2: Find refPropt2_valueBelow & refPropt2_valueAbove @ both (refPropt1_valueBelow and refPropt1_valueAbove)

    #                      | refPropt1_valueBelow | refPropt1_queryValue | refPropt1_valueAbove
    # -----------------------------------------------------------------------------------------
    # refPropt2_valueBelow | FIND:      rP1b_rP2b |                      | FIND:      rP1a_rP2b
    # refPropt2_queryValue | CALCULATE: rP1b_rP2q -> FINAL  CALCULATION <- CALCULATE: rP1a_rP2q
    # refPropt2_valueAfter | FIND:      rP1b_rP2a |                      | FIND:      rP1a_rP2a

    # refPropt1 -> x, refPropt2 -> y
    xVals = sorted(set(pair[0] for pair in pairs))
    xVals_available_yVals = {xVal: set(pair[1] for pair in pairs if pair[0] == xVal) for xVal in xVals}

    xVals_less = xVals[: (index := bisect_left(xVals, refPropt1_queryValue))]
    xVals_more = xVals[index:]

    # if all(values != [] for values in [xVals_less, xVals_more]):

    minimumDiagonal = 10 ** 5
    minimumDiagonal_surroundingValues = {}

    # Iterate over values of x surrounding the queryValue of x (= refPropt1_queryValue)
    t1 = time()
    for xVal_less in reversed(xVals_less):  # reversed -> gradually move away (left) from the x queryValue

        for xVal_more in xVals_more:  # gradually move away (right) from the x queryValue
            assert xVal_less <= refPropt1_queryValue <= xVal_more

            xVal_less_available_yVals = xVals_available_yVals[xVal_less]  # y values at which this xVal has states defined
            xVal_more_available_yVals = xVals_available_yVals[xVal_more]

            commonlyAvailable_yVals = sorted(xVal_less_available_yVals.intersection(xVal_more_available_yVals))  # yVals shared by both xVals

            # Check if there are at least 2 common yVals to begin with...
            if len(commonlyAvailable_yVals) < 2:
                continue

            # If so, get the yVals just before and after (= surrounding) the query y value.
            # If they cannot be obtained (NeedsExtrapolationError), likely the common yVals all exist on one side of the y queryValue (all more or less than the query value)
            try:
                yVal_below, yVal_above = get_surroundingValues(commonlyAvailable_yVals, refPropt2_queryValue)
            except NeedsExtrapolationError:
                continue

            # Check if it is the smallest interpolation interval by comparing diagonal length
            if diagonal := ((xVal_more - xVal_less) ** 2 + (yVal_above - yVal_below) ** 2) ** 0.5 < minimumDiagonal:
                minimumDiagonal = diagonal
                minimumDiagonal_surroundingValues.update({refPropt1_name: (xVal_less, xVal_more), refPropt2_name: (yVal_below, yVal_above)})

    t2 = time()
    print('TimeNotification: 2DInterpolation - Time to iteratively find smallest suitable interpolation interval: {0} seconds'.format((t2 - t1) / 1000))

    return minimumDiagonal_surroundingValues


def to_Kelvin(oValue: Union[float, int], oUnit: str = 'deg_C'):
    return oValue + 273.15


def to_deg_C(oValue: Union[float, int], oUnit: str = 'K'):
    return oValue - 273.15