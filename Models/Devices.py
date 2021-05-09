
from typing import Dict, List

from Models.States import StatePure
from Methods.ThprOps import apply_isentropicEfficiency

from Utilities.Numeric import isNumeric, isWithin
from Utilities.PrgUtilities import twoList, LinearEquation


class Device:

    def __init__(self):

        self.state_in: StatePure = None
        self.state_out: StatePure = None

        # mainly to accommodate closed feedwater heaters' bundles (mixing chambers)
        self.parentDevice: Device = None

    def set_states(self, state_in: StatePure = None, state_out: StatePure = None):
        if state_in is not None:
            self.state_in = state_in
        if state_out is not None:
            self.state_out = state_out

    def set_or_verify(self, setDict: Dict):
        for parameterName in setDict:
            if hasattr(self, parameterName):
                if not isNumeric(getattr(self, parameterName)):
                    setattr(self, parameterName, setDict[parameterName])
                else:
                    assert isWithin(getattr(self, parameterName), 3, '%', setDict[parameterName])

    @property
    def endStates(self):
        return twoList([state for state in [self.state_in, self.state_out] if isinstance(state, StatePure)])

class WorkDevice(Device):

    def __init__(self, eta_isentropic: float = 1):
        super(WorkDevice, self).__init__()

        self.eta_isentropic = eta_isentropic

        self.states_out: List[StatePure] = []
        # states_out is the list of all outlet states from the turbine. Flows may be extracted from the turbine at different stages with different pressures.
        # However it is expected that there is only one state_in.

    def set_states(self, state_in: StatePure = None, state_out: StatePure = None):
        if state_in is not None:
            self.state_in = state_in
        if state_out is not None:
            self.states_out.append(state_out)

    @property
    def endStates(self):
        all_endStates = [self.state_in]
        for endState in self.states_out:
            all_endStates.append(endState)
        return all_endStates


class Compressor(WorkDevice):
    def __init__(self, eta_isentropic: float = 1):
        super(Compressor, self).__init__(eta_isentropic)

class IGasCompressor(Compressor):
    pass


class Pump(WorkDevice):
    def __init__(self, eta_isentropic: float = 1):
        super(Pump, self).__init__(eta_isentropic)


class Turbine(WorkDevice):
    def __init__(self, eta_isentropic: float = 1):
        super(Turbine, self).__init__(eta_isentropic)

    def set_states(self, state_in: StatePure = None, state_out: StatePure = None):
        """This method is overridden for turbines. Proposed state_in is compared with the existing state_in (if one has already been set), and the existing state_in is replaced with the
        proposed one only if the pressure of the proposed state_in is higher than the pressure of the existing. This is done since pressure is expected to fall continuously through the turbine.
        In cases of regeneration, flows may be extracted from the turbine. Flows continuing through the turbine (those not extracted) will have an items list which includes the state at which
        extraction is made, then the turbine, and then the state they leave the turbine. When the flow items list is evaluated to set state references for the turbine, the intermediate state at
        which extraction is made may be wrongly assumed to be the state_in of the whole turbine. The comparison of proposed state_in to that of the existing one ensures that the set state_in is the
        very initial state at which all flows enter the turbine."""

        if state_in is not None:
            current_state_in = self.state_in
            proposed_state_in = state_in

            # state_in of the turbine should be the very first state_in.
            if current_state_in is not None:
                if current_state_in.P < proposed_state_in.P:
                    self.states_out.append(current_state_in)
                    self.state_in = proposed_state_in
                else:
                    if proposed_state_in is not current_state_in:
                        if proposed_state_in not in self.states_out:
                            self.states_out.append(proposed_state_in)
            else:
                self.state_in = proposed_state_in

        if state_out is not None:
            if state_out not in self.states_out:
                self.states_out.append(state_out)


class HeatDevice(Device):
    def __init__(self, infer_constant_P: bool = True):
        super(HeatDevice, self).__init__()

        self._infer_constant_pressure = infer_constant_P
        self.sHeatSupplied = float('nan')

    def infer_constant_pressure(self):
        """Sets or verifies pressures of end states to be equal in all lines."""
        number_ofNumericPvals = sum(1 for state in self.endStates if isNumeric(getattr(state, 'P')))
        endStates = self.endStates
        if number_ofNumericPvals == 2:
            assert isWithin(endStates[0].P, 3, '%', endStates[1].P)
        elif number_ofNumericPvals == 1:
            state_withNonNumericPval = endStates.itemSatisfying(lambda state: not isNumeric(getattr(state, 'P')))
            state_withNumericPval = endStates.other(state_withNonNumericPval)
            state_withNonNumericPval.P = state_withNumericPval.P

    def get_sHeatSuppliedExpression(self, forFlow: 'Flow' = None):  # forFlow is here for compatibility - see ReheatBoiler for real usage
        return [(1, (self.state_out, 'h')), (-1, (self.state_in, 'h'))]

class Combustor(HeatDevice):
    def __init__(self):
        super(Combustor, self).__init__()


class Boiler(HeatDevice):
    def __init__(self, *args, **kwargs):
        super(Boiler, self).__init__(**kwargs)


class Intercooler(HeatDevice):
    pass


class ReheatBoiler(HeatDevice):
    def __init__(self, T_exit_fixed: float = float('nan'), infer_constant_lineP: bool = True, infer_fixed_exitT: bool = True):
        super(ReheatBoiler, self).__init__()

        self._infer_constant_linePressures = infer_constant_lineP
        self.lines: List[twoList[StatePure]] = []
        self.sHeatSupplied = float('nan')
        # assumes pressure remains constant in each line passing through device, e.g. if a boiler is used twice by the same flow, each time, the pressure of the line
        # passing through the boiler will be different but the pressure inside the line will be constant - effectively, sets the inlet and outlet states of each line
        # passing through boiler to have the same pressure.

        self._infer_fixed_exitT = infer_fixed_exitT
        self.T_exit_fixed = T_exit_fixed
        # assumes each line passing through the boiler reaches the same exit temperature. Once an exit temperature is available, sets T_exit_fixed.

    def set_states(self, state_in: StatePure = None, state_out: StatePure = None):

        if (line_endStates := twoList([state_in, state_out])) not in self.lines:
            self.lines.append(line_endStates)
            # Set state_in, state_out as the currently set pair - but ideally, when making use of endStates of HeatDevices, methods must make provisions for lines
            self.state_in = state_in
            self.state_out = state_out

    @property
    def endStates(self):
        """All end states of the device, from all lines."""
        all_endStates = []
        for line in self.lines:
            for endState in line:
                all_endStates.append(endState)
        return all_endStates

    def infer_constant_pressure(self):
        """Sets or verifies pressures of end states to be equal in all lines."""
        for line_endStates in self.lines:
            number_ofNumericPvals = sum(1 for state in line_endStates if isNumeric(getattr(state, 'P')))
            if number_ofNumericPvals == 2:
                assert isWithin(line_endStates[0].P, 3, '%', line_endStates[1].P)
            elif number_ofNumericPvals == 1:
                state_withNonNumericPval = line_endStates.itemSatisfying(lambda state: not isNumeric(getattr(state, 'P')))
                state_withNumericPval = line_endStates.other(state_withNonNumericPval)
                state_withNonNumericPval.P = state_withNumericPval.P

    def infer_fixed_exitT(self):
        """Sets or verifies temperatures of *outlet states* *of all lines* to be equal."""
        state_out_withNumericT = None
        # Find a numeric state_out temperature - if none exist, the value will be None
        for line_endStates in self.lines:
            if line_endStates[1].hasDefined('T'):
                state_out_withNumericT = line_endStates[1]
                break

        if state_out_withNumericT is not None:
            self.set_or_verify({'T_exit_fixed': state_out_withNumericT.T})
            for line_endStates in self.lines:
                try:
                    line_endStates[1].set_or_verify({'T': self.T_exit_fixed})
                except AssertionError:
                    print('InputError: Boiler is configured to infer fixed exit temperature, i.e. assumes all entering flows leave at same temperature.\n'
                          'Line consisting of {0} \nthrough the boiler has input data at its exit state conflicting with the inferred fixed exit temperature of {1}.'.format(line_endStates, self.T_exit_fixed))

    def get_sHeatSuppliedExpression(self, forFlow: 'Flow' = None):
        # forFlow: Reheat boilers have multiple lines passing through them. Both lines do not have to belong to the same flow. When total heat supplied in flows is calculated, each HeatDevice's
        # get_sHeatSuppliedExpression method is called. When the method is called on rhboilers, if no provision is made for from which flow the method is called, the method will return the equation
        # giving the sum of heat supplied in all lines, not all of which may belong to the same flow, or more importantly not to the flow from which the method is called. Relying on the assumption that this method
        # will be called only when cycle level solution is made, and assuming that all states have been converted to FlowPoints by then (i.e. states know which flow they belong to), this method checks
        # if each line belongs to the calling flow, and builds the expression of heat supplied only for that flow.
        toReturn = []
        for line_endStates in self.lines:
            if forFlow is None or all(line_endState.flow is forFlow for line_endState in line_endStates):
                toReturn += [ (1, (line_endStates[1], 'h')), (-1, (line_endStates[0], 'h')) ]
        return toReturn

class Condenser(HeatDevice):
    def __init__(self):
        super(Condenser, self).__init__()


class MixingChamber(Device):
    def __init__(self, infer_common_mixingPressure: bool = True):
        super(MixingChamber, self).__init__()

        self._infer_common_mixingPressure = infer_common_mixingPressure

        self.states_in: List[StatePure] = []
        self.state_out: StatePure = None

    @property
    def endStates(self) -> List[StatePure]:
        """Returns all end states, i.e. the single outlet state and the 1+ inlet state."""
        all_endStates = [self.state_out]
        for endState in self.states_in:
            if isinstance(endState, StatePure):
                all_endStates.append(endState)
        return all_endStates

    def set_states(self, state_in: StatePure = None, state_out: StatePure = None):
        """Mixing chambers accept multiple in flows and provides one out flow. Provided "state_in"s are appended to states_in list, and provided state_out is made the state_out."""
        if state_in is not None and state_in not in self.states_in:
            self.states_in.append(state_in)
        if state_out is not None:
            self.state_out = state_out

    def infer_common_mixingPressure(self):
        """Sets or verifies pressures of all end states to be equal."""
        states_withKnownPressure = [state for state in self.endStates if state.hasDefined('P')]
        if states_withKnownPressure != []:
            samplePressure = states_withKnownPressure[0].P
            for state in self.endStates:
                state.set_or_verify({'P': samplePressure})


class ClosedFWHeater(HeatDevice):
    def __init__(self, *args, **kwargs):
        super(ClosedFWHeater, self).__init__(**kwargs)
        # Exit temperatures of lines passing through CFWH don't have to be the same. -> infer_fixed_exitT = False

        self.bundles = []
        # Each bundle is collection of flows coming in and leaving as one flow.

    class Bundle(Device):
        def __init__(self):
            super(ClosedFWHeater.Bundle, self).__init__()
            self.states_in: List[StatePure] = []
            self.state_out: StatePure = None
            self.parentDevice: Device = None

        def set_states(self, state_in: StatePure, state_out: StatePure):
            if state_in not in self.states_in:
                self.states_in.append(state_in)
            self.state_out = state_out

    def add_newBundle(self) -> Bundle:
        """Creates a new bundle (= mixing chamber), appends it to the bundles list, and returns the reference to it."""
        bundle = self.Bundle()
        bundle.parentDevice = self
        self.bundles.append(bundle)
        return bundle


class OpenFWHeater(MixingChamber):
    def __init__(self, *args, **kwargs):
        super(OpenFWHeater, self).__init__(*args, **kwargs)


class HeatExchanger(Device):
    def __init__(self, T_exit_fixed: float = float('nan'), infer_constant_lineP: bool = True, infer_common_exitT: bool = False):
        super(HeatExchanger, self).__init__()

        self.lines: List[twoList[StatePure]] = []
        self._infer_constant_linePressures = infer_constant_lineP  # sets the inlet and outlet states of each line passing through heat exchanger to have the same pressure.
        self._infer_common_exitTemperatures = infer_common_exitT  # sets the exit temperature of both lines to be equal

    def set_states(self, state_in: StatePure = None, state_out: StatePure = None):
        """Registers a new line, starting with state_in and ending with state_out, i.e. appends [state_in, state_out] to lines list. Additionally, sets the state_in and state_out attributes
        of the device as the provided ones. These attributes should not be used in heat exchangers - instead, lines should be processed. However these attributes are kept for compatibility reasons."""
        if (line_endStates := twoList([state_in, state_out])) not in self.lines:
            self.lines.append(line_endStates)
            # Set state_in, state_out as the currently set pair - but ideally, when making use of endStates of HeatDevices, methods must make provisions for lines
            self.state_in = state_in
            self.state_out = state_out

    @property
    def endStates(self):
        """All end states of the device, from all lines."""
        all_endStates = []
        for line in self.lines:
            for endState in line:
                all_endStates.append(endState)
        return all_endStates

    def infer_constant_linePressures(self):
        """Sets or verifies pressures of end states to be equal in all lines."""
        for line_endStates in self.lines:
            number_ofNumericPvals = sum(1 for state in line_endStates if isNumeric(getattr(state, 'P')))
            if number_ofNumericPvals == 2:
                assert isWithin(line_endStates[0].P, 3, '%', line_endStates[1].P)
            elif number_ofNumericPvals == 1:
                state_withNonNumericPval = line_endStates.itemSatisfying(lambda state: not isNumeric(getattr(state, 'P')))
                state_withNumericPval = line_endStates.other(state_withNonNumericPval)
                state_withNonNumericPval.P = state_withNumericPval.P

    def infer_common_exitTemperatures(self):
        """Sets the exit state temperature of all lines to be equal."""
        line_exitStates = [line_endStates[1] for line_endStates in self.lines]
        numeric_exitStateTvals = [line_exitState.T for line_exitState in line_exitStates if isNumeric(line_exitState.T)]
        if len(numeric_exitStateTvals) > 0:
            for line_exitState in line_exitStates:
                line_exitState.set_or_verify({'T': numeric_exitStateTvals[0]})

class ThrottlingValve:
    def __init__(self):
        pass


class Trap(Device):
    def __init__(self, infer_constant_enthalpy: bool = True):
        super(Trap, self).__init__()

        self._infer_constant_enthalpy = infer_constant_enthalpy

    def infer_constant_enthalpy(self):
        """Sets or verifies specific enthalpies of all end states to be equal."""
        sampleEnthalpy = self.endStates[0].h
        for state in self.endStates:
            state.set_or_verify({'h': sampleEnthalpy})


