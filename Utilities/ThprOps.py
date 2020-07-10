from pandas import DataFrame

from typing import Union, Dict, Tuple
from bisect import bisect_left, bisect_right

from Utilities.Exceptions import FeatureNotAvailableError
from Utilities.Numeric import isNumeric, interpolate_1D, isApproximatelyEqual, get_rangeEndpoints
from Properties.States import StatePure


def get_satPropts_byPT(materialPropertyDF: DataFrame, P: Union[float, int] = float('nan'), T: Union[float, int] = float('nan')) -> Tuple[StatePure, StatePure]:
    """Returns saturation properties at the provided pressure or temperature for the material whose materialPropertyDF is provided."""
    # at least the T or P must be provided

    def interpolate_onSatCurve(interpolate_by: str, interpolate_at: float, endpoint: str):

        endpoint_x = {'f': 0, 'g': 1}
        x = endpoint_x[endpoint]

        queryPropt, queryValue = interpolate_by, interpolate_at

        satStates_ordered_byPropt = materialPropertyDF.query('x == {0}'.format(x)).sort_values(queryPropt)  # retrieve only saturated liquid states
        satStates_ProptVals = satStates_ordered_byPropt[queryPropt].to_list()

        proptVal_below, proptVal_above = satStates_ProptVals[bisect_left(satStates_ProptVals, queryPropt) - 1], satStates_ProptVals[bisect_right(satStates_ProptVals, queryPropt)]
        satState_below, satState_above = materialPropertyDF.query('x == {0} and {1} == {2}'.format(x, queryPropt, proptVal_below)), materialPropertyDF.query('x == {0} and {1} == {2}'.format(x, queryPropt, proptVal_above))
        assert all(not state_DFrow.empty for state_DFrow in [satState_below, satState_above])

        satState_below, satState_above = StatePure().init_fromDFRow(satState_below), StatePure().init_fromDFRow(satState_above)

        satState_atProptVal = interpolate_betweenPureStates(satState_below, satState_above, interpolate_at={queryPropt: queryValue})
        assert satState_atProptVal.isFullyDefined()
        materialPropertyDF.append(satState_atProptVal.get_asDict_allProperties(), ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again


    if isNumeric(P):

        satLiq_atP = materialPropertyDF.query('P == {0} and x == 0'.format(P))
        if satLiq_atP.empty:
            # exact state (saturated liquid at P - state denoted "_f") not found

            satLiqs_ordered_byPressure = materialPropertyDF.query('x == 0').sort_values('P')  # retrieve only saturated liquid states
            satLiqs_pressures = satLiqs_ordered_byPressure['P'].to_list()

            pressureBelow, pressureAbove = satLiqs_pressures[bisect_left(satLiqs_pressures, P) - 1], satLiqs_pressures[bisect_right(satLiqs_pressures, P)]
            satLiq_belowP, satLiq_aboveP = materialPropertyDF.query('x == 0 and P == {0}'.format(pressureBelow)), materialPropertyDF.query('x == 0 and P == {0}'.format(pressureAbove))
            assert all(not state_DFrow.empty for state_DFrow in [satLiq_belowP, satLiq_aboveP])

            satLiq_belowP, satLiq_aboveP = StatePure().init_fromDFRow(satLiq_belowP), StatePure().init_fromDFRow(satLiq_aboveP)

            satLiq_atP = interpolate_betweenPureStates(satLiq_belowP, satLiq_aboveP, interpolate_at={'P': P})
            assert satLiq_atP.isFullyDefined()
            materialPropertyDF.append(satLiq_atP.get_asDict_allProperties(), ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again
        else:
            # if query found direct match (saturated liquid state at pressure), convert DFRow to a StatePure object
            satLiq_atP = StatePure(satLiq_atP.to_dict())
            assert satLiq_atP.isFullyDefined()

        satVap_atP = materialPropertyDF.query('P == {0} and x == 1'.format(P))
        if satVap_atP.empty:
            # exact state (saturated vapor at P - state denoted "_g") not found

            satVaps_ordered_byPressure = materialPropertyDF.query('x == 1').sort_values('P')  # retrieve only saturated vapor states
            satVaps_pressures = satVaps_ordered_byPressure['P'].to_list()

            pressureBelow, pressureAbove = satVaps_pressures[bisect_left(satVaps_pressures, P) - 1], satVaps_pressures[bisect_right(satVaps_pressures, P)]
            satVap_belowP, satVap_aboveP = materialPropertyDF.query('x == 1 and P == {0}'.format(pressureBelow)), materialPropertyDF.query('x == 1 and P == {0}'.format(pressureAbove))
            assert all(not state_DFrow.empty for state_DFrow in [satVap_belowP, satVap_aboveP])

            satVap_belowP, satVap_aboveP = StatePure().init_fromDFRow(satVap_belowP), StatePure().init_fromDFRow(satVap_aboveP)

            satVap_atP = interpolate_betweenPureStates(satVap_belowP, satVap_aboveP, interpolate_at={'P': P})
            assert satVap_atP.isFullyDefined()
            materialPropertyDF.append(satVap_atP.get_asDict_allProperties(), ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again
        else:
            # if query found direct match (saturated vapor state at pressure), convert DFRow to a StatePure object
            satVap_atP = StatePure(satVap_atP.to_dict())
            assert satVap_atP.isFullyDefined()

        assert satLiq_atP.x == 0 and satVap_atP.x == 1
        assert satLiq_atP.T == satVap_atP.T
        if isNumeric(T):
            if not isApproximatelyEqual(satLiq_atP.T, T, 3):
                raise AssertionError('Provided saturation temperature and pressure do not match.')

        return satLiq_atP, satVap_atP


    elif isNumeric(T):

        satLiq_atT = materialPropertyDF.query('T == {0} and x == 0'.format(T))
        if satLiq_atT.empty:
            # exact state (saturated liquid at T - state denoted "_f") not found

            satLiqs_ordered_byTemperature = materialPropertyDF.query('x == 0').sort_values('T')  # retrieve only saturated liquid states
            satLiqs_temperatures = satLiqs_ordered_byTemperature['T'].to_list()

            temperatureBelow, temperatureAbove = satLiqs_temperatures[bisect_left(satLiqs_temperatures, T) - 1], satLiqs_temperatures[bisect_right(satLiqs_temperatures, T)]
            satLiq_belowT, satLiq_aboveT = materialPropertyDF.query('x == 0 and T == {0}'.format(temperatureBelow)), materialPropertyDF.query('x == 0 and T == {0}'.format(temperatureAbove))
            assert all(not state_DFrow.empty for state_DFrow in [satLiq_belowT, satLiq_aboveT])

            satLiq_belowT, satLiq_aboveT = StatePure().init_fromDFRow(satLiq_belowT), StatePure().init_fromDFRow(satLiq_aboveT)

            satLiq_atT = interpolate_betweenPureStates(satLiq_belowT, satLiq_aboveT, interpolate_at={'T': T})
            assert satLiq_atT.isFullyDefined()
            materialPropertyDF.append(satLiq_atT.get_asDict_allProperties(), ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again
        else:
            # if query found direct match (saturated liquid state at pressure), convert DFRow to a StatePure object
            satLiq_atT = StatePure().init_fromDFRow(satLiq_atT)
            assert satLiq_atT.isFullyDefined()

        satVap_atT = materialPropertyDF.query('T == {0} and x == 1'.format(T))
        if satVap_atT.empty:
            # exact state (saturated vapor at T - state denoted "_g") not found

            satVaps_ordered_byTemperature = materialPropertyDF.query('x == 1').sort_values('T')  # retrieve only saturated vapor states
            satVaps_temperatures = satVaps_ordered_byTemperature['T'].to_list()

            temperatureBelow, temperatureAbove = satVaps_temperatures[bisect_left(satVaps_temperatures, T) - 1], satVaps_temperatures[bisect_right(satVaps_temperatures, T)]
            satVap_belowT, satVap_aboveT = materialPropertyDF.query('x == 1 and T == {0}'.format(temperatureBelow)), materialPropertyDF.query('x == 1 and T == {0}'.format(temperatureAbove))
            assert all(not state_DFrow.empty for state_DFrow in [satVap_belowT, satVap_aboveT])

            satVap_belowT, satVap_aboveT = StatePure().init_fromDFRow(satVap_belowT), StatePure().init_fromDFRow(satVap_aboveT)

            satVap_atT = interpolate_betweenPureStates(satVap_belowT, satVap_aboveT, interpolate_at={'T': T})
            assert satVap_atT.isFullyDefined()
            materialPropertyDF.append(satVap_atT.get_asDict_allProperties(), ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again
        else:
            # if query found direct match (saturated vapor state at pressure), convert DFRow to a StatePure object
            satVap_atT = StatePure().init_fromDFRow(satVap_atT)
            assert satVap_atT.isFullyDefined()

        assert satLiq_atT.x == 0 and satVap_atT.x == 1

        return satLiq_atT, satVap_atT


def interpolate_betweenPureStates(pureState_1: StatePure, pureState_2: StatePure, interpolate_at: Dict, mode: str = 'linear') -> StatePure:
    interpolatedState = StatePure()
    assert len(keys := list(interpolate_at.keys())) == 1
    referenceProperty = keys[0]
    referenceValue = interpolate_at[referenceProperty]

    if mode != 'linear':
        raise FeatureNotAvailableError('Interpolation methods other than "linear"')
    else:
        x = [getattr(pureState_1, referenceProperty), getattr(pureState_2, referenceProperty)]

        for property in StatePure.properties_all:
            y = [getattr(pureState_1, property), getattr(pureState_2, property)]
            setattr(interpolatedState, property, interpolate_1D(x, y, referenceValue))

        return interpolatedState


def fullyDefine_StatePure(state: StatePure, materialPropertyDF: DataFrame):

    def queryNearbyStates(refProp1_name: str, refProp1_value: float, refProp1_ptolerance: float, refProp2_name: str, refProp2_value: float, refProp2_ptolerance: float) -> DataFrame:
        (refProp1_min, refProp1_max) = get_rangeEndpoints(refProp1_value, percentUncertainty=refProp1_ptolerance)
        (refProp2_min, refProp2_max) = get_rangeEndpoints(refProp2_value, percentUncertainty=refProp2_ptolerance)

        queryTerm = '{0} <= {1} <= {2} and {3} <= {4} <= {5}'.format(refProp1_min, refProp1_name, refProp1_max, refProp2_min, refProp2_name, refProp2_max)
        return materialPropertyDF.query(queryTerm)

    assert state.isFullyDefinable(), 'State not fully definable: need at least 2 intensive properties to be known.'
    availableProperties = state.get_asDict_definedProperties()

    saturated = (0 <= state.x <= 1)

    if saturated:
        if any(propertyName in availableProperties for propertyName in ['P', 'T']):
            satLiq_atP, satVap_atP = get_satPropts_byPT(materialPropertyDF, P=state.P, T=state.T)  # either state.P or state.T has to be known - pass both, it is ok if one is NaN
            if state.x == 0:
                return satLiq_atP
            elif state.x == 1:
                return satVap_atP
            else:  # saturated mixture with unique quality (not 0 or 1)
                return interpolate_betweenPureStates(satLiq_atP, satVap_atP, interpolate_at={'x': state.x})

    elif not saturated:  # material is not in a saturated mixture state

        if superheated := state.x == 2:
            if isNumeric(state.P) and isNumeric(state.T) and len(suphVaps_atP := materialPropertyDF.query('P == {0} and x == 2'.format(state.P)).index) != 0:
                suphVaps_atP = suphVaps_atP.sort_values('T')
                suphVaps_atP_temperatures = suphVaps_atP['T'].to_list()

                temperatureBelow, temperatureAbove = suphVaps_atP_temperatures[bisect_left(suphVaps_atP_temperatures, state.T) - 1], suphVaps_atP_temperatures[bisect_right(suphVaps_atP_temperatures, state.T)]
                suphVap_belowT = materialPropertyDF.query('x == 2 and P == {0} and T == {1}'.format(state.P, temperatureBelow))
                suphVap_aboveT = materialPropertyDF.query('x == 2 and P == {0} and T == {1}'.format(state.P, temperatureAbove))

                return interpolate_betweenPureStates(StatePure().init_fromDFRow(suphVap_belowT), StatePure().init_fromDFRow(suphVap_aboveT), interpolate_at={'T': state.T})


        (refProp1_name, refProp1_value), (refProp2_name, refProp2_value) = list(availableProperties.items())[:2]  # first 2 properties taken as reference properties - will use to find values of others

        initial_ptolerance = 0.5
        matchingStates = queryNearbyStates(refProp1_name, refProp1_value, initial_ptolerance, refProp2_name, refProp2_value, initial_ptolerance)

        if number_ofMatches := len(matchingStates.index) == 1:
            return StatePure().init_fromDFRow(matchingStates)
        else:
            if number_ofMatches > 1:
                # find closest among matches
                pass
            else:
                assert number_ofMatches == 0
                # query again with larger tolerance