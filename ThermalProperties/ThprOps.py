from pandas import DataFrame

from typing import Union, Dict, Tuple, List

from Utilities.Exceptions import FeatureNotAvailableError, NoSaturatedStateError
from Utilities.Numeric import isNumeric, interpolate_1D, isApproximatelyEqual, get_rangeEndpoints, isWithin, get_surroundingValues
from ThermalProperties.States import StatePure


def get_saturationTemperature_atP(materialPropertyDF: DataFrame, P: float) -> float:
    """Returns the saturation temperature at the provided pressure. **Interpolates** if state not available at given pressure."""

    if P > materialPropertyDF.mp.criticalPoint.P:
        # Cengel page 119: Above the critical state, there is no line that separates the compressed liquid region and the superheated vapor region.
        # However, it is customary to refer to the substance as superheated vapor at temperatures above the critical temperature and
        # as compressed liquid at temperatures below the critical temperature.
        return materialPropertyDF.mp.criticalPoint.T

    else:
        # Check if saturated states at provided P are available in the data
        saturatedStates = materialPropertyDF.query('P == {0} and 0 <= x <= 1'.format(P))

        if not saturatedStates.empty:
            # Saturated states at P provided in the table
            saturatedStates_temperatures = saturatedStates['T'].to_list()
            sample_saturationTemperature = saturatedStates_temperatures[0]
            assert all(saturationTemperature == sample_saturationTemperature for saturationTemperature in saturatedStates_temperatures), 'ThDataError: Not all saturated states at P = {0} are at the same temperature! - All saturated states are expected to occur at same T & P'.format(P)
            return sample_saturationTemperature

        else:
            # Saturated state at P not provided directly
            satLiq_atP = interpolate_onSaturationCurve(materialPropertyDF, interpolate_by='P', interpolate_at=P, endpoint='f')
            return satLiq_atP.T


def get_saturationPressure_atT(materialPropertyDF: DataFrame, T: float) -> float:
    """Returns the saturation pressure at the provided temperature. **Interpolates** if state not available at given temperature."""

    if T > materialPropertyDF.mp.criticalPoint.T:
        return materialPropertyDF.mp.criticalPoint.P

    else:
        # Check if saturated states at provided T are available in the data
        saturatedStates = materialPropertyDF.query('T == {0} and 0 <= x <= 1'.format(T))

        if not saturatedStates.empty:
            # Saturated states at T provided in the table
            saturatedStates_pressures = saturatedStates['P'].to_list()
            sample_saturationpressure = saturatedStates_pressures[0]
            assert all(saturationPressure == sample_saturationpressure for saturationPressure in saturatedStates_pressures), 'ThDataError: Not all saturated states at T = {0} are at the same pressure! - All saturated states are expected to occur at same T & P'.format(T)
            return sample_saturationpressure

        else:
            # Saturated state at T not provided directly
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
            assert isWithin(satLiq_atP.T, 3, '%', T), 'InputError: Provided saturation temperature and pressure do not match.'

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


def interpolate_onSaturationCurve(materialPropertyDF: DataFrame, interpolate_by: str, interpolate_at: float, endpoint: str) -> StatePure:
    """Method to interpolate along the saturation curve. Interpolates to find the state identified by 'endpoint' (either f or g, for saturated liquid or vapor states) (i.e. identifier
    for left or right side of the saturation curve), and by value ('interpolate_at') of the property ('interpolate_by')."""

    endpoint_x = {'f': 0, 'g': 1}
    x = endpoint_x[endpoint]

    queryPropt, queryValue = interpolate_by, interpolate_at  # rename for clarity in this method

    satStates_ordered_byPropt = materialPropertyDF.query('x == {0}'.format(x)).sort_values(queryPropt)  # retrieve only saturated liquid states
    satStates_ProptVals = satStates_ordered_byPropt[queryPropt].to_list()

    proptVal_below, proptVal_above = get_surroundingValues(satStates_ProptVals, queryValue) # satStates_ProptVals[bisect_left(satStates_ProptVals, queryValue) - 1], satStates_ProptVals[bisect_right(satStates_ProptVals, queryValue)]
    satState_below, satState_above = materialPropertyDF.query('x == {0} and {1} == {2}'.format(x, queryPropt, proptVal_below)), materialPropertyDF.query('x == {0} and {1} == {2}'.format(x, queryPropt, proptVal_above))
    assert all(not state_DFrow.empty for state_DFrow in [satState_below, satState_above]), 'More than one saturation state provided for the same value of query property "{0}" in supplied data file.'.format(queryPropt)

    satState_below, satState_above = StatePure().init_fromDFRow(satState_below), StatePure().init_fromDFRow(satState_above)

    satState_atProptVal = interpolate_betweenPureStates(satState_below, satState_above, interpolate_at={queryPropt: queryValue})
    assert satState_atProptVal.isFullyDefined()
    return satState_atProptVal


def fullyDefine_StatePure(state: StatePure, materialPropertyDF: DataFrame):

    def query_nearbyStates(refProp1_name: str, refProp1_value: float, refProp1_ptolerance: float,
                           refProp2_name: str, refProp2_value: float, refProp2_ptolerance: float,
                           addCond1_name: str, addCond1_value: float) -> DataFrame:

        (refProp1_min, refProp1_max) = get_rangeEndpoints(refProp1_value, percentUncertainty=refProp1_ptolerance)
        (refProp2_min, refProp2_max) = get_rangeEndpoints(refProp2_value, percentUncertainty=refProp2_ptolerance)
        queryTerm = '{0} <= {1} <= {2} and {3} <= {4} <= {5} and {6} == {7}'.format(refProp1_min, refProp1_name, refProp1_max, refProp2_min, refProp2_name, refProp2_max, addCond1_name, addCond1_value)
        return materialPropertyDF.query(queryTerm)

    assert state.isFullyDefinable(), 'State not fully definable: need at least 2 (independent) intensive properties to be known.'
    availableProperties = state.get_asDict_definedProperties()
    availablePropertiesNames = list(availableProperties.keys())
    non_referencePropertiesNames = [propertyName for propertyName in availablePropertiesNames if propertyName not in ['P', 'T']]
    P_available, T_available = ('P' in availablePropertiesNames), ('T' in availablePropertiesNames)

    # DETERMINE PHASE OF SUBSTANCE

    isSaturatedMixture = None

    # If quality is provided, phase is inferred
    if isNumeric(state.x):
        isSaturatedMixture = (0 <= state.x <= 1)

    # If quality is not provided, determine phase, then assign / calculate quality
    else:

        # Determine phase: Compare provided T to the saturation T at provided P
        if P_available and T_available:
            # If both P & T are provided, check if T is above saturation temperature at that P
            # Using the fact that P & T are not independent for saturated states - substance is saturated at known temperature and pressure

            saturationTemperature_atP = get_saturationTemperature_atP(materialPropertyDF, P=state.P)  # This can handle pressures at which no distinct saturation process exists

            if state.T == saturationTemperature_atP:
                # state.x needs to be calculated
                isSaturatedMixture = True
            elif state.T > saturationTemperature_atP:
                state.x = 2
                isSaturatedMixture = False
            elif state.T < saturationTemperature_atP:
                state.x = -1
                isSaturatedMixture = False

        # Determine phase
        elif P_available or T_available:

            # Compare provided P / T to critical P / T of substance - Check if there are even saturation states at the P/T to begin with. If there are, couldBe_saturatedMixture.
            couldBe_saturatedMixture = False

            if P_available:
                if state.P > materialPropertyDF.mp.criticalPoint.P:
                    isSaturatedMixture = False
                    state.x = 2
                else:
                    couldBe_saturatedMixture = True
            elif T_available:
                if state.T > materialPropertyDF.mp.criticalPoint.T:
                    isSaturatedMixture = False
                    state.x = 2
                else:
                    couldBe_saturatedMixture = True

            # Determine phase: Saturated states do exist at the provided P / T. Check if saturated mixture with P / T and 1 other property
            if couldBe_saturatedMixture:
                # Is provided u/h/s/mu between saturation limits at the provided T/P?

                satLiq_atRef, satVap_atRef = get_saturationPropts(materialPropertyDF, P=state.P, T=state.T)

                # Define lambda function to check if value of a non-reference property (i.e. property other than P/T) is within the saturated mixture limits
                isWithinSaturationZone = lambda propertyName, propertyValue: getattr(satLiq_atRef, propertyName) <= propertyValue <= getattr(satVap_atRef, propertyName)
                isSuperheated = lambda propertyName, propertyValue: getattr(satVap_atRef, propertyName) < propertyValue
                isSubcooled = lambda propertyName, propertyValue: propertyValue < getattr(satLiq_atRef, propertyName)

                # Check if the first available non-reference property has value within saturation limits
                isSaturatedMixture = isWithinSaturationZone(non_referencePropertiesNames[0], getattr(state, non_referencePropertiesNames[0]))

                # All non-reference properties should give the same result - if the first one is found to be within saturation limits, all should be so.
                assert all(isSaturatedMixture == isWithinSaturationZone(propertyName, getattr(state, propertyName)) for propertyName in non_referencePropertiesNames), 'ThDataError: While defining state {0}, property {1} suggests saturated state (value within saturation limits), but other properties do not.'.format(state, non_referencePropertiesNames[0])
                if isSaturatedMixture:
                    # Calculate state.x using the first available non-reference property
                    calcProptName, calcProptValue = non_referencePropertiesNames[0], availableProperties[non_referencePropertiesNames[0]]
                    state.x = (calcProptValue - getattr(satLiq_atRef, calcProptName))/(getattr(satVap_atRef, calcProptName) - getattr(satLiq_atRef, calcProptName))

                else:
                    superheated = isSuperheated(non_referencePropertiesNames[0], getattr(state, non_referencePropertiesNames[0]))
                    # Check if first non-ref propt suggests suph, then assert all other non-ref propts to suggest the same
                    assert all(superheated == isSuperheated(propertyName, getattr(state, propertyName)) for propertyName in non_referencePropertiesNames), 'ThDataError: While defining state {0}, property {1} suggests superheated state (value above saturation limits), but other properties do not.'.format(state, non_referencePropertiesNames[0])

                    if superheated:
                        state.x = 2
                    else:
                        subcooled = isSubcooled(non_referencePropertiesNames[0], getattr(state, non_referencePropertiesNames[0]))
                        # Check if first non-ref propt suggests subc, then assert all other non-ref propts to suggest the same
                        assert all(subcooled == isSubcooled(propertyName, getattr(state, propertyName)) for propertyName in non_referencePropertiesNames), 'ThDataError: While defining state {0}, property {1} suggests subcooled state (value below saturation limits), but other properties do not.'.format(state, non_referencePropertiesNames[0])

                        if subcooled:
                            state.x = -1
                        else:
                            raise AssertionError('Error: While checking if state is saturated using P or T as reference, could not determine if state is subcooled / saturated / superheated.')

        # Determine phase: Neither P / T of the state provided
        else:
            # Determine if saturated or not using properties other than P/T - P/T not available
            isSaturatedMixture = False
            raise FeatureNotAvailableError('State definition with variables other than at least P / T')

        # By now, it should have been determined whether state is a saturated (mixture) and state.x should have been defined.
        assert isSaturatedMixture is not None and isNumeric(state.x)

    # Fully define state: State is saturated (mixture)
    if isSaturatedMixture:
        if P_available or T_available:
            satLiq_atP, satVap_atP = get_saturationPropts(materialPropertyDF, P=state.P, T=state.T)  # either state.P or state.T has to be known - pass both, it is ok if one is NaN
            if state.x == 0:
                return satLiq_atP
            elif state.x == 1:
                return satVap_atP
            else:  # saturated mixture with unique quality (not 0 or 1)
                return interpolate_betweenPureStates(satLiq_atP, satVap_atP, interpolate_at={'x': state.x})
        else:
            # Define saturated state with properties other than P/T
            pass

    # Fully define state: State is not saturated (mixture)
    else:
        # Superheated vapor
        if state.x == 2:

            refPropt1, refPropt2 = availablePropertiesNames[:2]  # first 2 available properties used as reference
            refPropt1_queryValue, refPropt2_queryValue = [availableProperties[property] for property in [refPropt1, refPropt2]]
            refPropts = [(refPropt1, refPropt1_queryValue), (refPropt2, refPropt2_queryValue)]

            # Check if exact state available
            exactState = materialPropertyDF.cq.cQuery({refPropt1: refPropt1_queryValue, refPropt2: refPropt2_queryValue})

            if not exactState.empty:
                if len(exactState.index) == 1:
                    return StatePure().init_fromDFRow(exactState)
                else:
                    # Found multiple states with same P & T - need to pick one
                    # TODO - Pick one
                    raise AssertionError('NotImplementedError: Multiple states satisfying same conditions found.')

            # Exact state not available
            else:
                # Check if 1D interpolation possible
                _1d_interpolationCheck = {}

                # Check if either refPropt1_queryValue or refPropt2_queryValue has data available
                for refProptCurrent_index, (refProptCurrent_name, refProptCurrent_queryValue) in enumerate(refPropts):

                    suphVaps_at_refProptCurrent = materialPropertyDF.cq.cQuery({refProptCurrent_name: refProptCurrent_queryValue, 'x': 2})

                    if not suphVaps_at_refProptCurrent.empty:
                        # If so, get refProptOther and its interpolation gap (gap between available values)

                        refProptOther_name, refProptOther_queryValue = refPropts[refProptCurrent_index - 1]
                        values_of_refProptOther = suphVaps_at_refProptCurrent[refProptOther_name].to_list()

                        refProptOther_valueBelow, refProptOther_valueAbove = get_surroundingValues(values_of_refProptOther, refProptOther_queryValue)
                        gap_betweenValues = abs(refProptOther_valueAbove - refProptOther_valueBelow)

                        _1d_interpolationCheck.update({refProptCurrent_name: {'1D_interpolatable': True, 'gap': gap_betweenValues,
                                                                              'refProptOther': {'name': refProptOther_name, 'surroundingValues': (refProptOther_valueBelow, refProptOther_valueAbove)}}})

                    else:
                        _1d_interpolationCheck.update({refProptCurrent_name: {'1D_interpolatable': False, 'gap': None}})

                # Pick reference property to hold constant: pick the one where the interpolation interval for the other refPropt is minimum
                # Future: consider picking one where the gap between query value and an endpoint is the minimum

                minimumGap = 10**5  # arbitrary large value
                refPropt_for_minimumGap_in1Dinterpolation = None

                for refProptCurrent_name in _1d_interpolationCheck:
                    if _1d_interpolationCheck[refProptCurrent_name]['1D_interpolatable']:
                        if (gap_of_refProptCurrent := _1d_interpolationCheck[refProptCurrent_name]['gap']) < minimumGap:
                            minimumGap = gap_of_refProptCurrent
                            refPropt_for_minimumGap_in1Dinterpolation = refProptCurrent_name

                if refPropt_for_minimumGap_in1Dinterpolation is not None:
                    # At least one refPropt allows 1D interpolation. If multiple does, the one where the other has the minimum interpolation gap has been picked

                    refPropt_name = refPropt_for_minimumGap_in1Dinterpolation
                    refPropt_value = availableProperties[refPropt_name]

                    refProptOther_name = _1d_interpolationCheck[refPropt_name]['refProptOther']['name']
                    refProptOther_queryValue = availableProperties[refProptOther_name]
                    refProptOther_valueBelow, refProptOther_valueAbove = _1d_interpolationCheck[refPropt_name]['refProptOther']['surroundingValues']

                    state_with_refProptOther_valueBelow = StatePure().init_fromDFRow(materialPropertyDF.cq.cQuery({refPropt_name: refPropt_value,
                                                                                                                   refProptOther_name: refProptOther_valueBelow, 'x': 2}))

                    state_with_refProptOther_valueAbove = StatePure().init_fromDFRow(materialPropertyDF.cq.cQuery({refPropt_name: refPropt_value,
                                                                                                                   refProptOther_name: refProptOther_valueAbove, 'x': 2}))

                    return interpolate_betweenPureStates(state_with_refProptOther_valueBelow, state_with_refProptOther_valueAbove, interpolate_at={refProptOther_name: refProptOther_queryValue})

                else:
                    # Double Interpolation needed

                    for refProptCurrent_index, (refProptCurrent_name, refProptCurrent_queryValue) in enumerate(refPropts):
                        refProptOther_name, refProptOther_queryValue = refPropts[refProptCurrent_index - 1]

                        # refProptCurrent: Find refProptCurrent_valueBelow & refProptCurrent_valueAbove
                        refProptCurrent_valueBelow, refProptCurrent_valueAbove = get_surroundingValues(materialPropertyDF.cq.superheatedStates[refProptCurrent_name].to_list(), refProptCurrent_queryValue)


                        # refPropt1: Find refPropt1_valueBelow & refPropt1_valueAbove
                        refPropt1_valueBelow, refPropt1_valueAbove = get_surroundingValues(materialPropertyDF.cq.superheatedStates[refPropt1].to_list(), refPropt1_queryValue)


                    # refPropt2: Find refPropt2_valueBelow & refPropt2_valueAbove @ both (refPropt1_valueBelow and refPropt1_valueAbove)


                    # Construct:
                    #                      | refPropt1_valueBelow | refPropt1_queryValue | refPropt1_valueAbove
                    # -----------------------------------------------------------------------------------------
                    # refPropt2_valueBelow |         FIND         |                      |         FIND
                    # refPropt2_queryValue |  CALCULATE (1Dintp)  | >FINAL  CALCULATION< |  CALCULATE (1Dintp)
                    # refPropt2_valueAfter |         FIND         |                      |         FIND

                    # At each valueBelow / valueAfter query, make sure they exist! If one does not, needs extrapolation - not going to do it!


                    pass

