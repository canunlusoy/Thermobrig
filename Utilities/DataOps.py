from pandas import DataFrame


from typing import Union, List, Dict, OrderedDict, Tuple
from bisect import bisect_left, bisect_right

from Utilities.Numeric import isNumeric, interpolate_1D
from Properties.States import StatePure


def process_MaterialPropertyDF(materialPropertyDF: DataFrame):
    # TODO
    return materialPropertyDF





def get_saturationProperties(materialPropertyDF: DataFrame, P: Union[float, int] = float('nan'), T: Union[float, int] = float('nan')) -> Tuple[StatePure]:
    """Returns saturation properties at the provided pressure or temperature for the material whose materialPropertyDF is provided."""

    if isNumeric(P):

        satLiq_atP = materialPropertyDF.query('P == @{0} and x == 0'.format(P))
        if satLiq_atP.empty:
            # exact state (saturated liquid at P - state denoted "_f") not found

            satLiqs_ordered_byPressure = materialPropertyDF.query('x == 0').sort_values('P')  # retrieve only saturated liquid states
            satLiqs_pressures = satLiqs_ordered_byPressure['P'].to_list()

            pressureBelow, pressureAbove = satLiqs_pressures[bisect_left(satLiqs_pressures, P) - 1], satLiqs_pressures[bisect_right(satLiqs_pressures, P)]
            satLiq_belowP, satLiq_aboveP = materialPropertyDF.query('x == 0 and P == @{0}'.format(pressureBelow)), materialPropertyDF.query('x == 0 and P == @{0}'.format(pressureAbove))
            assert all(not state_DFrow.empty for state_DFrow in [satLiq_belowP, satLiq_aboveP])

            satLiq_belowP, satLiq_aboveP = StatePure(satLiq_belowP.to_dict()), StatePure(satLiq_aboveP.to_dict())

            satLiq_atP = interpolate_betweenPureStates(satLiq_belowP, satLiq_aboveP, interpolate_at={'P': P})
            assert satLiq_atP.isFullyDefined()
            materialPropertyDF.append(satLiq_atP, ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again
        # else:
        #     satLiq_atP = StatePure()


        satVap_atP = materialPropertyDF.query('P == @{0} and x == 1'.format(P))
        if satVap_atP.empty:
            # exact state (saturated vapor at P - state denoted "_g") not found

            satVaps_ordered_byPressure = materialPropertyDF.query('x == 1').sort_values('P')  # retrieve only saturated vapor states
            satVaps_pressures = satVaps_ordered_byPressure['P'].to_list()

            pressureBelow, pressureAbove = satVaps_pressures[bisect_left(satVaps_pressures, P) - 1], satVaps_pressures[bisect_right(satVaps_pressures, P)]
            satVap_belowP, satVap_aboveP = materialPropertyDF.query('x == 1 and P == @{0}'.format(pressureBelow)), materialPropertyDF.query('x == 0 and P == @{0}'.format(pressureAbove))
            assert all(not state_DFrow.empty for state_DFrow in [satVap_belowP, satVap_aboveP])

            satVap_belowP, satVap_aboveP = StatePure(satVap_belowP.to_dict()), StatePure(satVap_aboveP.to_dict())

            satVap_atP = interpolate_betweenPureStates(satVap_belowP, satVap_aboveP, interpolate_at={'P': P})
            assert satVap_atP.isFullyDefined()
            materialPropertyDF.append(satVap_atP, ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again

        if isNumeric(T):

            pass


        return satLiq_atP, satVap_atP

    elif isNumeric(T):
        pass
     # at least the T or P must be provided


class FeatureNotAvailableError(Exception):
    def __init__(self, featureName: str = None):
        feature = 'Feature'
        if featureName is not None:
            feature = featureName
        super(FeatureNotAvailableError, self).__init__('{} not implemented'.format(feature))



def interpolate_betweenPureStates(pureState_1: StatePure, pureState_2: StatePure, interpolate_at: Dict, mode: str = 'linear') -> StatePure:
    if mode != 'linear':
        raise FeatureNotAvailableError('Interpolation methods other than "linear"')
    else:
        interpolatedState = StatePure()

        assert len(keys := list(interpolate_at.keys())) == 1
        referenceProperty = keys[0]
        referenceValue = interpolate_at[referenceProperty]
        x = [getattr(pureState_1, referenceProperty), getattr(pureState_2, referenceProperty)]

        for property in StatePure.properties_all:
            y = [getattr(pureState_1, property), getattr(pureState_2, property)]
            setattr(interpolatedState, property, interpolate_1D(x, y, referenceValue))

        return interpolatedState
