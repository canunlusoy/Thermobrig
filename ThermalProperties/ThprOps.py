from pandas import DataFrame

from typing import Union, Dict, Tuple
from bisect import bisect_left, bisect_right

from Utilities.Exceptions import FeatureNotAvailableError, NoSaturatedStateError
from Utilities.Numeric import isNumeric, interpolate_1D, isApproximatelyEqual, get_rangeEndpoints, isWithin
from ThermalProperties.States import StatePure


def get_saturationTemperature_atP(materialPropertyDF: DataFrame, P: float) -> float:
    """Returns the saturation temperature at the provided pressure. **Interpolates** if state not available at given pressure."""
    saturatedStates = materialPropertyDF.query('P == {0} and 0 <= x <= 1'.format(P))
    if not saturatedStates.empty:
        saturatedStates_temperatures = saturatedStates['T'].to_list()
        sample_saturationTemperature = saturatedStates_temperatures[0]
        assert all(saturationTemperature == sample_saturationTemperature for saturationTemperature in saturatedStates_temperatures), 'ThDataError: Not all saturated states at P = {0} are at the same temperature! - All saturated states are expected to occur at same T & P'.format(P)
        return sample_saturationTemperature
    else:
        satLiq_atP = interpolate_onSaturationCurve(materialPropertyDF, interpolate_by='P', interpolate_at=P, endpoint='f')
        return satLiq_atP.T


def get_saturationPressure_atT(materialPropertyDF: DataFrame, T: float) -> float:
    """Returns the saturation pressure at the provided temperature. **Interpolates** if state not available at given temperature."""
    saturatedStates = materialPropertyDF.query('T == {0} and 0 <= x <= 1'.format(T))
    if not saturatedStates.empty:
        saturatedStates_pressures = saturatedStates['P'].to_list()
        sample_saturationpressure = saturatedStates_pressures[0]
        assert all(saturationPressure == sample_saturationpressure for saturationPressure in saturatedStates_pressures), 'ThDataError: Not all saturated states at T = {0} are at the same pressure! - All saturated states are expected to occur at same T & P'.format(T)
        return sample_saturationpressure
    else:
        satLiq_atT = interpolate_onSaturationCurve(materialPropertyDF, interpolate_by='T', interpolate_at=T, endpoint='f')
        return satLiq_atT.T


def get_saturationPropts(materialPropertyDF: DataFrame, P: Union[float, int] = float('nan'), T: Union[float, int] = float('nan')) -> Tuple[StatePure, StatePure]:
    """Returns saturation properties at the provided pressure or temperature for the material whose materialPropertyDF is provided."""
    # at least the T or P must be provided

    if isNumeric(P):

        satLiq_atP = materialPropertyDF.query('P == {0} and x == 0'.format(P))
        if satLiq_atP.empty:
            # exact state (saturated liquid at P - state denoted "_f") not found
            satLiq_atP = interpolate_onSaturationCurve(materialPropertyDF, interpolate_by='P', interpolate_at=P, endpoint='f')
            materialPropertyDF.append(satLiq_atP.get_asDict_allProperties(), ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again
        else:
            # if query found direct match (saturated liquid state at pressure), convert DFRow to a StatePure object
            satLiq_atP = StatePure().init_fromDFRow(satLiq_atP)

        satVap_atP = materialPropertyDF.query('P == {0} and x == 1'.format(P))
        if satVap_atP.empty:
            # exact state (saturated vapor at P - state denoted "_g") not found
            satVap_atP = interpolate_onSaturationCurve(materialPropertyDF, interpolate_by='P', interpolate_at=P, endpoint='g')
            materialPropertyDF.append(satVap_atP.get_asDict_allProperties(), ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again
        else:
            # if query found direct match (saturated vapor state at pressure), convert DFRow to a StatePure object
            satVap_atP = StatePure().init_fromDFRow(satVap_atP)

        assert satLiq_atP.isFullyDefined() and satVap_atP.isFullyDefined()
        assert satLiq_atP.x == 0 and satVap_atP.x == 1
        assert satLiq_atP.T == satVap_atP.T

        if isNumeric(T):
            if not isWithin(satLiq_atP.T, 3, '%', T):
                raise AssertionError('Provided saturation temperature and pressure do not match.')

        return satLiq_atP, satVap_atP

    elif isNumeric(T):

        satLiq_atT = materialPropertyDF.query('T == {0} and x == 0'.format(T))
        if satLiq_atT.empty:
            # exact state (saturated liquid at T - state denoted "_f") not found
            satLiq_atT = interpolate_onSaturationCurve(materialPropertyDF, interpolate_by='T', interpolate_at=T, endpoint='f')
            materialPropertyDF.append(satLiq_atT.get_asDict_allProperties(), ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again
        else:
            # if query found direct match (saturated liquid state at pressure), convert DFRow to a StatePure object
            satLiq_atT = StatePure().init_fromDFRow(satLiq_atT)

        satVap_atT = materialPropertyDF.query('T == {0} and x == 1'.format(T))
        if satVap_atT.empty:
            # exact state (saturated vapor at T - state denoted "_g") not found
            satVap_atT = interpolate_onSaturationCurve(materialPropertyDF, interpolate_by='T', interpolate_at=T, endpoint='g')
            materialPropertyDF.append(satVap_atT.get_asDict_allProperties(), ignore_index=True)  # append the calculated (interpolated) state to materialProperty table for future use in runtime if needed - won't have to interpolate again
        else:
            # if query found direct match (saturated vapor state at pressure), convert DFRow to a StatePure object
            satVap_atT = StatePure().init_fromDFRow(satVap_atT)

        assert satLiq_atT.isFullyDefined() and satVap_atT.isFullyDefined()
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


def interpolate_onSaturationCurve(materialPropertyDF: DataFrame, interpolate_by: str, interpolate_at: float, endpoint: str):
    """Method to interpolate along the saturation curve. Interpolates to find the state identified by 'endpoint' (either f or g, for saturated liquid or vapor states) (i.e. identifier
    for left or right side of the saturation curve), and by value ('interpolate_at') of the property ('interpolate_by')."""

    endpoint_x = {'f': 0, 'g': 1}
    x = endpoint_x[endpoint]

    queryPropt, queryValue = interpolate_by, interpolate_at  # rename for clarity in this method

    satStates_ordered_byPropt = materialPropertyDF.query('x == {0}'.format(x)).sort_values(queryPropt)  # retrieve only saturated liquid states
    satStates_ProptVals = satStates_ordered_byPropt[queryPropt].to_list()

    proptVal_below, proptVal_above = satStates_ProptVals[bisect_left(satStates_ProptVals, queryValue) - 1], satStates_ProptVals[bisect_right(satStates_ProptVals, queryValue)]
    satState_below, satState_above = materialPropertyDF.query('x == {0} and {1} == {2}'.format(x, queryPropt, proptVal_below)), materialPropertyDF.query('x == {0} and {1} == {2}'.format(x, queryPropt, proptVal_above))
    assert all(not state_DFrow.empty for state_DFrow in [satState_below, satState_above]), 'More than one saturation state provided for the same value of query property "{0}" in supplied data file.'.format(queryPropt)

    satState_below, satState_above = StatePure().init_fromDFRow(satState_below), StatePure().init_fromDFRow(satState_above)

    satState_atProptVal = interpolate_betweenPureStates(satState_below, satState_above, interpolate_at={queryPropt: queryValue})
    assert satState_atProptVal.isFullyDefined()
    return satState_atProptVal


def fullyDefine_StatePure(state: StatePure, materialPropertyDF: DataFrame):

    def queryNearbyStates(refProp1_name: str, refProp1_value: float, refProp1_ptolerance: float, refProp2_name: str, refProp2_value: float, refProp2_ptolerance: float) -> DataFrame:
        (refProp1_min, refProp1_max) = get_rangeEndpoints(refProp1_value, percentUncertainty=refProp1_ptolerance)
        (refProp2_min, refProp2_max) = get_rangeEndpoints(refProp2_value, percentUncertainty=refProp2_ptolerance)

        queryTerm = '{0} <= {1} <= {2} and {3} <= {4} <= {5}'.format(refProp1_min, refProp1_name, refProp1_max, refProp2_min, refProp2_name, refProp2_max)
        return materialPropertyDF.query(queryTerm)

    assert state.isFullyDefinable(), 'State not fully definable: need at least 2 (independent) intensive properties to be known.'
    availableProperties = state.get_asDict_definedProperties()
    availablePropertiesNames = list(availableProperties.keys())
    non_referenceProperties = [propertyName for propertyName in availablePropertiesNames if propertyName not in ['P', 'T']]

    # Check if saturated
    if isNumeric(state.x):
        # Quality already provided
        saturated = (0 <= state.x <= 1)
    else:
        # Quality unknown

        if all(propertyName in availablePropertiesNames for propertyName in ['P', 'T']):
            # If both P & T are provided, check if T is above saturation temperature at that P
            # Using the fact that P & T are not independent for saturated states - substance is saturated at known temperature and pressure

            saturationTemperature_atP = get_saturationTemperature_atP(materialPropertyDF, P=state.P)
            # TODO - Handle: no saturated state may exist at given P!

            if state.T == saturationTemperature_atP:
                # state.x needs to be calculated
                saturated = True
            elif state.T > saturationTemperature_atP:
                state.x = 2
                saturated = False
            elif state.T < saturationTemperature_atP:
                state.x = -1
                saturated = False



        elif any(propertyName in availablePropertiesNames for propertyName in ['P', 'T']):
            # Are there saturated states at the provided P/T?
            # If so, is provided u/h/s/mu between saturation limits at the provided T/P?




            satLiq_atRef, satVap_atRef = get_saturationPropts(materialPropertyDF, P=state.P, T=state.T)

            # Define lambda function to check if value of a non-reference property (i.e. property other than P/T) is within the saturated mixture limits
            isWithinSaturationZone = lambda propertyName, propertyValue: getattr(satLiq_atRef, propertyName) <= propertyValue <= getattr(satVap_atRef, propertyName)
            isSuperheated = lambda propertyName, propertyValue: getattr(satVap_atRef, propertyName) < propertyValue
            isSubcooled = lambda propertyName, propertyValue: propertyValue < getattr(satLiq_atRef, propertyName)

            # Check if the first available non-reference property has value within saturation limits
            saturated = isWithinSaturationZone(non_referenceProperties[0], getattr(state, non_referenceProperties[0]))

            # All non-reference properties should give the same result - if the first one is found to be within saturation limits, all should be so.
            assert all(saturated == isWithinSaturationZone(propertyName, getattr(state, propertyName)) for propertyName in non_referenceProperties), 'ThDataError: While defining state {0}, property {1} suggests saturated state (value within saturation limits), but other properties do not.'.format(state, non_referenceProperties[0])
            if saturated:
                # Calculate state.x using the first available non-reference property
                calcProptName, calcProptValue = non_referenceProperties[0], availableProperties[non_referenceProperties[0]]
                state.x = (calcProptValue - getattr(satLiq_atRef, calcProptName))/(getattr(satVap_atRef, calcProptName) - getattr(satLiq_atRef, calcProptName))

            else:
                superheated = isSuperheated(non_referenceProperties[0], getattr(state, non_referenceProperties[0]))
                # Check if first non-ref propt suggests suph, then assert all other non-ref propts to suggest the same
                assert all(superheated == isSuperheated(propertyName, getattr(state, propertyName)) for propertyName in non_referenceProperties), 'ThDataError: While defining state {0}, property {1} suggests superheated state (value above saturation limits), but other properties do not.'.format(state, non_referenceProperties[0])

                if superheated:
                    state.x = 2
                else:
                    subcooled = isSubcooled(non_referenceProperties[0], getattr(state, non_referenceProperties[0]))
                    # Check if first non-ref propt suggests subc, then assert all other non-ref propts to suggest the same
                    assert all(subcooled == isSubcooled(propertyName, getattr(state, propertyName)) for propertyName in non_referenceProperties), 'ThDataError: While defining state {0}, property {1} suggests subcooled state (value below saturation limits), but other properties do not.'.format(state, non_referenceProperties[0])

                    if subcooled:
                        state.x = -1
                    else:
                        raise AssertionError('Error: While checking if state is saturated using P or T as reference, could not determine if state is subcooled / saturated / superheated.')

        else:
            # Determine if saturated or not using properties other than P/T - P/T not available
            saturated = False
            pass

        # At the end of this else block, state.x should have been defined.
        assert isNumeric(state.x)

    if saturated:
        # state.x must have been determined above
        if any(propertyName in availablePropertiesNames for propertyName in ['P', 'T']):
            satLiq_atP, satVap_atP = get_saturationPropts(materialPropertyDF, P=state.P, T=state.T)  # either state.P or state.T has to be known - pass both, it is ok if one is NaN
            if state.x == 0:
                return satLiq_atP
            elif state.x == 1:
                return satVap_atP
            else:  # saturated mixture with unique quality (not 0 or 1)
                return interpolate_betweenPureStates(satLiq_atP, satVap_atP, interpolate_at={'x': state.x})
        else:
            # Determine saturated state with properties other than P/T
            pass

    elif not saturated:  # material is not in a saturated mixture state

        if superheated := state.x == 2:
            if isNumeric(state.P) and isNumeric(state.T) and len((suphVaps_atP := materialPropertyDF.query('P == {0} and x == 2'.format(state.P))).index) != 0:
                suphVaps_atP = suphVaps_atP.sort_values('T')
                suphVaps_atP_temperatures = suphVaps_atP['T'].to_list()

                temperatureBelow, temperatureAbove = suphVaps_atP_temperatures[bisect_left(suphVaps_atP_temperatures, state.T) - 1], suphVaps_atP_temperatures[bisect_right(suphVaps_atP_temperatures, state.T)]
                suphVap_belowT = materialPropertyDF.query('x == 2 and P == {0} and T == {1}'.format(state.P, temperatureBelow))
                suphVap_aboveT = materialPropertyDF.query('x == 2 and P == {0} and T == {1}'.format(state.P, temperatureAbove))

                return interpolate_betweenPureStates(StatePure().init_fromDFRow(suphVap_belowT), StatePure().init_fromDFRow(suphVap_aboveT), interpolate_at={'T': state.T})


        (refProp1_name, refProp1_value), (refProp2_name, refProp2_value) = list(availableProperties.items())[:2]  # first 2 properties taken as reference properties - will use to find values of others

        initial_ptolerance = 0.5

        # TODO - Query to include quality!
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