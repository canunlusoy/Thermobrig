from pandas import DataFrame

from typing import Union, Dict, Tuple, List
from bisect import bisect_left
from time import time

from Utilities.Exceptions import FeatureNotAvailableError, NoSaturatedStateError, NeedsExtrapolationError
from Utilities.Numeric import isNumeric, interpolate_1D, isApproximatelyEqual, get_rangeEndpoints, isWithin, get_surroundingValues, to_Kelvin, to_deg_C
from Models.States import StatePure, StateIGas


def get_saturationTemperature_atP(mpDF: DataFrame, P: float) -> float:
    """Returns the saturation temperature at the provided pressure. **Interpolates** if state not available at given pressure."""

    if P > mpDF.mp.criticalPoint.P:
        # Cengel page 119: Above the critical state, there is no line that separates the compressed liquid region and the superheated vapor region.
        # However, it is customary to refer to the substance as superheated vapor at temperatures above the critical temperature and
        # as compressed liquid at temperatures below the critical temperature.
        return mpDF.mp.criticalPoint.T

    else:
        # Check if saturated states at provided P are available in the data
        saturatedStates = mpDF.query('P == {0} and 0 <= x <= 1'.format(P))

        if not saturatedStates.empty:
            # Saturated states at P provided in the table
            saturatedStates_temperatures = saturatedStates['T'].to_list()
            sample_saturationTemperature = saturatedStates_temperatures[0]
            assert all(saturationTemperature == sample_saturationTemperature for saturationTemperature in saturatedStates_temperatures), 'ThDataError: Not all saturated states at P = {0} are at the same temperature! - All saturated states are expected to occur at same T & P'.format(P)
            return sample_saturationTemperature

        else:
            # Saturated state at P not provided directly
            satLiq_atP = interpolate_onSaturationCurve(mpDF, interpolate_by='P', interpolate_at=P, endpoint='f')
            return satLiq_atP.T


def get_saturationPressure_atT(mpDF: DataFrame, T: float) -> float:
    """Returns the saturation pressure at the provided temperature. **Interpolates** if state not available at given temperature."""

    if T > mpDF.mp.criticalPoint.T:
        return mpDF.mp.criticalPoint.P

    else:
        # Check if saturated states at provided T are available in the data
        saturatedStates = mpDF.query('T == {0} and 0 <= x <= 1'.format(T))

        if not saturatedStates.empty:
            # Saturated states at T provided in the table
            saturatedStates_pressures = saturatedStates['P'].to_list()
            sample_saturationpressure = saturatedStates_pressures[0]
            assert all(saturationPressure == sample_saturationpressure for saturationPressure in saturatedStates_pressures), 'ThDataError: Not all saturated states at T = {0} are at the same pressure! - All saturated states are expected to occur at same T & P'.format(T)
            return sample_saturationpressure

        else:
            # Saturated state at T not provided directly
            satLiq_atT = interpolate_onSaturationCurve(mpDF, interpolate_by='T', interpolate_at=T, endpoint='f')
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

        for property in pureState_1._properties_all:  # not using reference to general class definition, since state may be StatePure or StateIGas
            y = [getattr(pureState_1, property), getattr(pureState_2, property)]
            setattr(interpolatedState, property, interpolate_1D(x, y, referenceValue))

        return interpolatedState


def interpolate_onSaturationCurve(mpDF: DataFrame, interpolate_by: str, interpolate_at: float, endpoint: str) -> StatePure:
    """Method to interpolate along the saturation curve. Interpolates to find the state identified by 'endpoint' (either f or g, for saturated liquid or vapor states) (i.e. identifier
    for left or right side of the saturation curve), and by value ('interpolate_at') of the property ('interpolate_by')."""

    endpoint_x = {'f': 0, 'g': 1}
    x = endpoint_x[endpoint]

    queryPropt, queryValue = interpolate_by, interpolate_at  # rename for clarity in this method

    satStates_ordered_byPropt = mpDF.query('x == {0}'.format(x)).sort_values(queryPropt)  # retrieve only saturated liquid states
    satStates_ProptVals = satStates_ordered_byPropt[queryPropt].to_list()

    proptVal_below, proptVal_above = get_surroundingValues(satStates_ProptVals, queryValue) # satStates_ProptVals[bisect_left(satStates_ProptVals, queryValue) - 1], satStates_ProptVals[bisect_right(satStates_ProptVals, queryValue)]
    satState_below, satState_above = mpDF.query('x == {0} and {1} == {2}'.format(x, queryPropt, proptVal_below)), mpDF.query('x == {0} and {1} == {2}'.format(x, queryPropt, proptVal_above))
    assert all(not state_DFrow.empty for state_DFrow in [satState_below, satState_above]), 'More than one saturation state provided for the same value of query property "{0}" in supplied data file.'.format(queryPropt)

    satState_below, satState_above = StatePure().init_fromDFRow(satState_below), StatePure().init_fromDFRow(satState_above)

    satState_atProptVal = interpolate_betweenPureStates(satState_below, satState_above, interpolate_at={queryPropt: queryValue})
    assert satState_atProptVal.isFullyDefined()
    return satState_atProptVal


def fullyDefine_StatePure(state: StatePure, mpDF: DataFrame):
    """Fully defines StatePure objects by looking them up / interpolating on the material property table."""

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

            saturationTemperature_atP = get_saturationTemperature_atP(mpDF, P=state.P)  # This can handle pressures at which no distinct saturation process exists

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
                if state.P > mpDF.mp.criticalPoint.P:
                    isSaturatedMixture = False
                    state.x = 2
                else:
                    couldBe_saturatedMixture = True
            elif T_available:
                if state.T > mpDF.mp.criticalPoint.T:
                    isSaturatedMixture = False
                    state.x = 2
                else:
                    couldBe_saturatedMixture = True

            # Determine phase: Saturated states do exist at the provided P / T. Check if saturated mixture with P / T and 1 other property
            if couldBe_saturatedMixture:
                # Is provided u/h/s/mu between saturation limits at the provided T/P?

                satLiq_atRef, satVap_atRef = get_saturationPropts(mpDF, P=state.P, T=state.T)

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
            # TODO
            isSaturatedMixture = False
            raise FeatureNotAvailableError('State definition with variables other than at least P / T')

        # By now, it should have been determined whether state is a saturated (mixture) and state.x should have been defined.
        assert isSaturatedMixture is not None and isNumeric(state.x)

    # Fully define state: State is saturated (mixture)
    if isSaturatedMixture:
        if P_available or T_available:
            satLiq_atP, satVap_atP = get_saturationPropts(mpDF, P=state.P, T=state.T)  # either state.P or state.T has to be known - pass both, it is ok if one is NaN
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

        # Set phase_mpDF: section of main mpDF with states of only the same phase
        if state.x == 2:
            phase_mpDF = mpDF.cq.suphVaps
            phase = 'superheated'
        elif state.x == -1:
            phase_mpDF = mpDF.cq.subcLiqs
            phase = 'subcooled'
        else:
            # This would be a coding error - can be removed once confidence is established
            raise AssertionError('Error: Phase of state could not be determined - x value not -1, 0-1 or 2')

        refPropt1_name, refPropt2_name = availablePropertiesNames[:2]  # first 2 available properties used as reference  # TODO: If cannot be interpolated with these 2, can try others if provided
        refPropt1_queryValue, refPropt2_queryValue = [availableProperties[property] for property in [refPropt1_name, refPropt2_name]]
        refPropts = [(refPropt1_name, refPropt1_queryValue), (refPropt2_name, refPropt2_queryValue)]

        # Check if exact state available
        exactState = mpDF.cq.cQuery({refPropt1_name: refPropt1_queryValue, refPropt2_name: refPropt2_queryValue})

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

                states_at_refProptCurrent = phase_mpDF.cq.cQuery({refProptCurrent_name: refProptCurrent_queryValue})

                if not states_at_refProptCurrent.empty and len(states_at_refProptCurrent.index) > 1:  # there should be more than one state at refProptCurrent to interpolate between
                    # If so, get refProptOther and its interpolation gap (gap between available values)

                    refProptOther_name, refProptOther_queryValue = refPropts[refProptCurrent_index - 1]
                    values_of_refProptOther = states_at_refProptCurrent[refProptOther_name].to_list()

                    try:
                        refProptOther_valueBelow, refProptOther_valueAbove = get_surroundingValues(values_of_refProptOther, refProptOther_queryValue)
                    except NeedsExtrapolationError:
                        _1d_interpolationCheck.update({refProptCurrent_name: {'1D_interpolatable': False, 'gap': None}})
                        continue

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
                # 1D INTERPOLATION
                # At least one refPropt allows 1D interpolation. If multiple does, the one where the other has the minimum interpolation gap has been picked

                refPropt_name = refPropt_for_minimumGap_in1Dinterpolation
                refPropt_value = availableProperties[refPropt_name]

                refProptOther_name = _1d_interpolationCheck[refPropt_name]['refProptOther']['name']
                refProptOther_queryValue = availableProperties[refProptOther_name]
                refProptOther_valueBelow, refProptOther_valueAbove = _1d_interpolationCheck[refPropt_name]['refProptOther']['surroundingValues']

                state_with_refProptOther_valueBelow = StatePure().init_fromDFRow(phase_mpDF.cq.cQuery({refPropt_name: refPropt_value,
                                                                                                       refProptOther_name: refProptOther_valueBelow}))

                state_with_refProptOther_valueAbove = StatePure().init_fromDFRow(phase_mpDF.cq.cQuery({refPropt_name: refPropt_value,
                                                                                                       refProptOther_name: refProptOther_valueAbove}))

                return interpolate_betweenPureStates(state_with_refProptOther_valueBelow, state_with_refProptOther_valueAbove, interpolate_at={refProptOther_name: refProptOther_queryValue})

            else:
                # DOUBLE INTERPOLATION
                available_refProptPairs = list(phase_mpDF[[refPropt1_name, refPropt2_name]].itertuples(index=False, name=None))

                # refPropt1 -> x, refPropt2 -> y

                xVals = sorted(set(pair[0] for pair in available_refProptPairs))
                xVals_available_yVals = {xVal: set(pair[1] for pair in available_refProptPairs if pair[0] == xVal) for xVal in xVals}

                xVals_less = xVals[: (index := bisect_left(xVals, refPropt1_queryValue))]  # list of available xValues less than query value available in states
                xVals_more = xVals[index:]  # same for available xValues more than query value

                # Iterate over values of x surrounding the queryValue of x (= refPropt1_queryValue)
                t1 = time()

                # Strategy: First find 2 states:
                # one with x value less than refPropt1_queryValue but with y value = refPropt2_queryValue
                # one with x value more than refPropt1_queryValue but with y value = refPropt2_queryValue
                # i.e. two states surround the requested state in terms of x.
                # To find these 2 states, iterate over available xValues more than and less than the x query value. At each iteration, TRY to get the 2 surrounding values of y available for that x.
                # There may not be 2 values of y available at each x value surrounding the queried y value. In such case, try/except clause continues iteration with a new x value.
                # Once at an x value, 2 values of y surrounding the y query value are found, interpolate between the states with (xVal, yVal_below) and (xVal, yVal_above)
                # The outmost for loop does this for both state with x value less than x query value and state with x value more than x query value.

                states_at_y_queryValue = []  # list of states at which y = refPropt2 value is the query value, but x = refPropt1 value is not the query value.

                for available_xValList in [reversed(xVals_less), xVals_more]:

                    for xVal in available_xValList:
                        xVal_available_yVals = xVals_available_yVals[xVal]

                        try:
                            yVal_below, yVal_above = get_surroundingValues(xVal_available_yVals, refPropt2_queryValue)
                        except NeedsExtrapolationError:
                            continue

                        state_at_xVal_less_yVal_below = StatePure().init_fromDFRow(phase_mpDF.cq.cQuery({refPropt1_name: xVal, refPropt2_name: yVal_below}))
                        state_at_xVal_less_yVal_above = StatePure().init_fromDFRow(phase_mpDF.cq.cQuery({refPropt1_name: xVal, refPropt2_name: yVal_above}))

                        states_at_y_queryValue.append(interpolate_betweenPureStates(state_at_xVal_less_yVal_below, state_at_xVal_less_yVal_above, interpolate_at={refPropt2_name: refPropt2_queryValue}))
                        break

                t2 = time()
                print('TimeNotification: 2DInterpolation - Time to iteratively find smallest suitable interpolation interval: {0} seconds'.format((t2 - t1) / 1000))

                if len(states_at_y_queryValue) == 2:
                    return interpolate_betweenPureStates(states_at_y_queryValue[0], states_at_y_queryValue[1], interpolate_at={refPropt1_name: refPropt1_queryValue})
                else:
                    # 2 states to interpolate between could not be found
                    if state.x == -1 and T_available:
                        # SATURATED LIQUID APPROXIMATION AT SAME TEMPERATURE FOR SUBCOOLED LIQUIDS
                        return get_saturationPropts(phase_mpDF, T=state.T)[0]  # returns [satLiq, satVap], pick first
                    else:
                        raise NeedsExtrapolationError('DataError InputError: No {0} states with values of {1} lower or higher than the query value of {2} are available in the data table.'.format(phase.upper(), refPropt1_name, refPropt1_queryValue))


def apply_IGasLaw(state: StateIGas, R: float):
    """Uses Ideal Gas Law to find missing properties, if possible. If all variables in the Ideal Gas Law are already defined, checks consistency"""
    # P mu = R T
    IGasLaw_allProperties = ['P', 'mu', 'T']
    IGasLaw_availableProperties = [propertyName for propertyName in IGasLaw_allProperties if isNumeric(getattr(state, propertyName))]
    IGasLaw_missingProperties = [propertyName for propertyName in IGasLaw_allProperties if propertyName not in IGasLaw_availableProperties]

    if number_ofMissingProperties := len(IGasLaw_missingProperties) == 1:
        missingProperty = IGasLaw_missingProperties[0]
        if missingProperty == 'P':
            state.P = (R * to_Kelvin(state.T) / state.mu)
        elif missingProperty == 'mu':
            state.mu = (R * to_Kelvin(state.T) / state.P)
        elif missingProperty == 'T':
            state.T = to_deg_C(state.P * state.mu / R)
    elif number_ofMissingProperties == 0:
        # If all properties available, check consistency / compliance with the law
        assert to_Kelvin(state.T) == (state.P * state.mu / R), 'DataError InputError: Provided / inferred state properties not compliant with ideal gas law.'


def define_StateIGas(state: StateIGas, fluid: 'IdealGas'):
    """Tries to fill in the properties of an ideal gas state by applying the ideal gas law and looking up state on the provided mpDF."""

    if len(available_TDependentProperties := [propertyName for propertyName in fluid.mpDF.mp.availableProperties if propertyName in state._properties_all and isNumeric(getattr(state, propertyName))]) >= 1:
        refPropt_name = available_TDependentProperties[0]

        # Try finding exact state on mpDF
        state_at_refPropt = fluid.mpDF.cq.cQuery({refPropt_name: getattr(state, refPropt_name)})
        try:
            if state_at_refPropt.empty:
                # Interpolate in mpDF
                refPropt_valueBelow, refPropt_valueAbove = get_surroundingValues(fluid.mpDF[refPropt_name], value=getattr(state, refPropt_name))
                state_at_refPropt_valueBelow = StateIGas().init_fromDFRow(fluid.mpDF.cq.cQuery({refPropt_name: refPropt_valueBelow}))
                state_at_refPropt_valueAbove = StateIGas().init_fromDFRow(fluid.mpDF.cq.cQuery({refPropt_name: refPropt_valueAbove}))
                state_at_refPropt = interpolate_betweenPureStates(state_at_refPropt_valueBelow, state_at_refPropt_valueAbove, interpolate_at={refPropt_name: getattr(state, refPropt_name)})

            state.copy_fromState(state_at_refPropt)
        except NeedsExtrapolationError:
            pass

    apply_IGasLaw(state, fluid.R)
    return state


def apply_isentropicEfficiency(state_in: StatePure, state_out_ideal: StatePure, eta_isentropic: float, fluid: 'Fluid'):
    """Returns a new state_out based on the provided one, with all fields filled out based on the isentropic efficiency of the process between the state_in and state_out."""

    assert state_out_ideal.hasDefined('P')
    state_out_ideal.set_or_verify({'s': state_in.s})
    state_out_ideal.copy_fromState(fluid.define(state_out_ideal))
    state_out_actual = StatePure(P=state_out_ideal.P)
    work_ideal = state_out_ideal.h - state_in.h

    if work_ideal >= 0:
        # work provided to flow from device -> eta_s = w_ideal / w_actual
        work_actual = work_ideal / eta_isentropic
        state_out_actual.h = work_actual + state_in.h
    else:
        # work extracted from flow by device -> eta_s = w_actual / w_ideal
        work_ideal = abs(work_ideal)
        work_actual = eta_isentropic * work_ideal
        state_out_actual.h = state_in.h - work_actual

    assert state_out_actual.isFullyDefinable()
    return fluid.define(state_out_actual)

