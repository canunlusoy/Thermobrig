
from typing import Union, List, Dict

from Methods.ThprOps import apply_isentropicEfficiency, apply_incompressibleWorkRelation, apply_isentropicIGasProcess

from Models.States import StatePure, StateIGas
from Models.Fluids import Fluid, IdealGas
from Models.Devices import Device, WorkDevice, HeatDevice, MixingChamber, HeatExchanger, Trap, Turbine, Boiler, ReheatBoiler, Intercooler, Compressor, GasReheater, Combustor, Pump

from Utilities.Numeric import isNumeric, isWithin
from Utilities.PrgUtilities import twoList, LinearEquation, setattr_fromAddress, solve_solvableEquations, updateEquations
from Utilities.Exceptions import DataVerificationError

# FLOWS include relations between states (same T / P / h / s)
# CYCLES include relations between flows (mass fractions, energy transfers)

class Flow:

    def __init__(self, workingFluid: Fluid, massFlowRate: float = float('nan'), massFlowFraction: float = float('nan'), constant_c: bool = False):

        # Not considering flows with multiple fluids, one flow can contain only one fluid
        self.workingFluid = workingFluid
        self.massFR = massFlowRate
        self.massFF = massFlowFraction

        # Flow analysis setting
        self.constant_c = constant_c
        if self.constant_c:
            assert isNumeric(self.workingFluid.cp) and isNumeric(self.workingFluid.k)

        self.items = []
        # Items is a list of devices and states making up the flow.
        # If flow is cyclic, items list should start with a state and end with the same state.

        self._equations = []
        self._updatedUnknowns = set()

        self._initialSolutionComplete = False

        self.log = None
        self.callbacks = None


    @property
    def states(self) -> List[StatePure]:
        return [item for item in self.items if isinstance(item, StatePure)]

    @property
    def devices(self) -> List[Device]:
        return [item for item in self.items if isinstance(item, Device)]

    @property
    def workDevices(self) -> List[WorkDevice]:
        return [item for item in self.items if isinstance(item, WorkDevice)]

    @property
    def heatDevices(self) -> List[HeatDevice]:
        return [item for item in self.items if isinstance(item, HeatDevice)]

    @property
    def net_sWorkExtracted(self):
        return self.get_net_sWorkExtracted(returnExpression=True)

    @property
    def sHeatSupplied(self):
        return self.get_sHeatSupplied(returnExpression=True)

    def isFullyDefined(self) -> bool:
        """Checks if all states in the flow are fully defined."""
        return all(state.isFullyDefined() for state in self.states)

    def get_undefinedStates(self) -> List[StatePure]:
        """Returns a list of states in the flow which are not fully defined."""
        toReturn = []
        for state in self.states:
            if not state.isFullyDefined() and state not in toReturn:
                toReturn.append(state)
        return toReturn

    def set_or_verify(self, setDict: Dict):
        for parameterName in setDict:
            if hasattr(self, parameterName):
                if not isNumeric(getattr(self, parameterName)):
                    setattr(self, parameterName, setDict[parameterName])
                else:
                    assert isWithin(getattr(self, parameterName), 3, '%', setDict[parameterName])

    def get_surroundingItems(self, item: Union[StatePure, Device], includeNone: bool = False) -> List[Union[StatePure, Device]]:
        """Returns a list of items before and after the provided item in the flow items list.
        If includeNone, if there is no surrounding value from one side, a None value is added in its place to the returned list."""
        surroundingItems = []
        if item in self.items:
            itemIndex = self.items.index(item)
            if itemIndex > 0:  # item is not the first item in items list, there is at least one more item before it
                surroundingItems.append(self.items[itemIndex - 1])
            elif includeNone:
                surroundingItems.append(None)
            if itemIndex < len(self.items) - 1:  # item is not the last item, there is at least one more item after it
                surroundingItems.append(self.items[itemIndex + 1])
            elif includeNone:
                surroundingItems.append(None)
        return surroundingItems

    def get_itemRelative(self, item, relativePosition: int):
        """Returns the flow item given by its position relative to the specified item. relativePosition of -1 returns the flow item prior to the provided item."""
        itemIndex = self.items.index(item)
        return self.items[itemIndex + relativePosition]

    def solve(self):
        self._define_definableStates()

        # Steps for INITIAL SOLUTION RUN
        if not self._initialSolutionComplete:

            for device in self.devices:
                self._solveDevice(device)

            self._define_definableStates()
            self._initialSolutionComplete = True
        # Initialization complete.

        undefinedStates_previousIteration = []
        iterationCounter = 0
        while (undefinedStates := self.get_undefinedStates()) != undefinedStates_previousIteration:  # continue as long as something new is resolved in the previous iteration
            # If new states became defined in the previous iteration, they may also help resolve other states.
            iterationCounter += 1
            print('Flow solution iteration #{0}'.format(iterationCounter))

            for state in undefinedStates:
                surroundingDevices = self.get_surroundingItems(state)
                for device in surroundingDevices:
                    if not state.isFullyDefined():  # the state may become defined in first iteration of loop
                        self._solveDevice(device)
                self._defineStates_ifDefinable(state)

            undefinedStates_previousIteration = undefinedStates

        updateEquations(self._equations, self._updatedUnknowns)
        solve_solvableEquations(self._equations)
        updateEquations(self._equations, self._updatedUnknowns)


    def _define_definableStates(self) -> None:
        """Runs the appropriate defFcn (function to fully define the state properties) for states which can be fully defined, i.e. has 2+ independent intensive properties defined."""
        self._defineStates_ifDefinable(self.states)

    def _defineStates_ifDefinable(self, states: Union[StatePure, List, twoList]):
        if isinstance(states, StatePure):
            states = [states]
        for state in states:
            if not state.isFullyDefined():  # Tries to define only undefined states! Doesn't process already defined states again!
                self.workingFluid.defineState_ifDefinable(state)

    def _set_devices_endStateReferences(self):
        """For each device in the items list, sets state_in as the preceding state in the items list, and sets state_out as the next state in the items list.
        If there are no states before or after the device in the items list, leaves the relevant reference empty."""
        self._check_itemsConsistency()
        maximumIndex = len(self.items) - 1
        for itemIndex, item in enumerate(self.items):
            if isinstance(item, Device):
                state_in, state_out = None, None  # set default references to None
                if itemIndex - 1 >= 0:  # if there is an item in the list before the device - guaranteed to be a state by _check_itemsConsistency
                    state_in = self.items[itemIndex - 1]
                if itemIndex + 1 <= maximumIndex:  # if there is an item in the list after the device
                    state_out = self.items[itemIndex + 1]
                item.set_states(state_in=state_in, state_out=state_out)

    def _check_itemsConsistency(self):
        """Check if items of flow are either states or devices, and if a state is always followed by a device or vice versa."""
        maximumIndex = len(self.items) - 1
        for itemIndex, item in enumerate(self.items):
            if isinstance(item, StatePure):
                if itemIndex < maximumIndex:
                    assert isinstance(self.items[itemIndex + 1], Device)
            elif isinstance(item, Device):
                if itemIndex < maximumIndex:
                    assert isinstance(self.items[itemIndex + 1], StatePure)
            else:
                raise AssertionError('InputError: Item {0} in items of flow {1} is not a device or a state.'.format(item, self))

    def _solveDevice(self, device: Device):
        endStates = device.endStates

        if isinstance(device, WorkDevice):
            # Apply isentropic efficiency relations to determine outlet state
            self.solve_workDevice(device)

        # if not self._initialSolutionComplete:  # the below processes do not need to be done in each flow solution iteration, but only for the initial one

        if isinstance(device, HeatDevice):
            # Setting end state pressures to be the same
            if device._infer_constant_pressure:
                device.infer_constant_pressure()

            if isinstance(device, ReheatBoiler):  # reheat boilers can have multiple lines.
                # Setting up fixed exit temperature if inferring exit temperature from one exit state
                if device._infer_fixed_exitT:
                    device.infer_fixed_exitT()

            elif isinstance(device, Intercooler):
                if device.coolTo == 'ideal':  # Cool to the temperature of the compressor inlet state
                    assert isinstance((compressorBefore := self.get_itemRelative(device, -2)), Compressor)  # before intercooler, there should be compressor exit state, and then a compressor
                    device.state_out.set_or_verify({'T': compressorBefore.state_in.T})
                else:  # Cool to specified temperature
                    assert isNumeric(device.coolTo)
                    device.state_out.set_or_verify({'T': device.coolTo})

            elif isinstance(device, GasReheater):
                if device.heatTo == 'ideal':  # Heat to the temperature of the turbine inlet state
                    assert isinstance((turbineBefore := self.get_itemRelative(device, -2)), Turbine)
                    device.state_out.set_or_verify({'T': turbineBefore.state_in.T})

                elif device.heatTo == 'heatSupplied':
                    if not self._initialSolutionComplete:
                        assert isNumeric(device.sHeatSupplied)
                        if not self.constant_c:
                            sHeatSuppliedRelation = LinearEquation(LHS=[(1, (device.state_out, 'h')), (-1, (device.state_in, 'h'))], RHS=device.sHeatSupplied)
                        else:
                            sHeatSuppliedRelation = LinearEquation(LHS=[(1, self.workingFluid.cp, (device.state_out, 'T')), (-1, self.workingFluid.cp, (device.state_in, 'T'))], RHS=device.sHeatSupplied)
                        self._equations.append(sHeatSuppliedRelation)

                        if sHeatSuppliedRelation.isSolvable():
                            solution = sHeatSuppliedRelation.solve()
                            unknownAddress = list(solution.keys())[0]
                            setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
                            self._updatedUnknowns.add(unknownAddress)
                        else:
                            sHeatSuppliedRelation.source = device
                            self._equations.append(sHeatSuppliedRelation)
                else:  # Heat to specified temperature
                    assert isNumeric(device.heatTo)
                    device.state_out.set_or_verify({'T': device.heatTo})

        elif isinstance(device, HeatExchanger):
            # Setting end state pressures along the same line if pressures is assumed constant along each line
            if device._infer_constant_linePressures:
                device.infer_constant_linePressures()

            # Setting temperature of exit states equal for all lines
            if device._infer_common_exitTemperatures:
                device.infer_common_exitTemperatures()  # not the ideal place - inter-flow operation should ideally be in cycle scope

        elif isinstance(device, MixingChamber):
            # Setting pressures of all in / out flows to the same value
            if device._infer_common_mixingPressure:
                device.infer_common_mixingPressure()

        elif isinstance(device, Trap):
            if device._infer_constant_enthalpy:
                device.infer_constant_enthalpy()

        self._defineStates_ifDefinable(endStates)

    def solve_workDevice(self, device: WorkDevice):
        """Determines outlet state based on available inlet state using isentropic efficiency."""
        # Find the state_out out of the device IN THIS FLOW - work devices may have multiple states_out (e.g. turbines with many extractions for reheat, regeneration).

        occurrences_ofDevice = [index for index, item in enumerate(self.items) if item is device]
        states_afterDevice: List[StatePure] = [self.items[index + 1] for index in occurrences_ofDevice if index + 1 < len(self.items)]  # state_afterDevice is a StatePure for sure after the check in _check_itemsConsistency

        # PRESSURE RATIO RELATION SETUP
        if not device._pressureRatioRelationSetup and len(states_afterDevice) == 1:
            self._add_pressureRatioRelation(device)  # To be done only once, for devices with a single exit state (excludes turbines with multiple extractions)

        # ISENTROPIC PROCESS RELATIONS
        if device.eta_isentropic == 1:
            device.set_endStateEntropiesEqual()  # Sets or verifies.

            if isinstance(self.workingFluid, IdealGas):
                for state_out in device.states_out:  # Can determine additional properties based on ideal gas isentropic process relations
                    apply_isentropicIGasProcess(constant_c=self.constant_c, state_in=device.state_in, state_out=state_out, fluid=self.workingFluid)  # sets, verifies, or does nothing

            self._defineStates_ifDefinable(device.endStates)  # if any states became definable with the above process

        # ISENTROPIC EFFICIENCY RELATIONS
        for state_out in states_afterDevice:
            if not isinstance(self.workingFluid, IdealGas) and (device.state_in.hasDefined('h') and state_out.hasDefined('P')):  # Used to check if state_in also hadNumeric 's'
                # going to overwrite state_out - TODO: Need to copy in the first time, then verify in subseqs - verify if eta_isentropic holds!
                state_out.copy_fromState(apply_isentropicEfficiency(constant_c=self.constant_c,
                                                                    state_in=device.state_in, state_out_ideal=state_out,
                                                                    eta_isentropic=device.eta_isentropic, fluid=self.workingFluid))
            elif isinstance(self.workingFluid, IdealGas):  # TODO: Do, or verify

                # FIND state_out FROM state_in
                if not state_out.hasDefined('T'):  # common case: find state_out based on state_in
                    state_out_ideal = StateIGas().copy_fromState(state_out)
                    apply_isentropicIGasProcess(constant_c=self.constant_c, fluid=self.workingFluid, state_in=device.state_in, state_out=state_out_ideal)
                    state_out_actual = apply_isentropicEfficiency(constant_c=self.constant_c, state_in=device.state_in, state_out_ideal=state_out_ideal, eta_isentropic=device.eta_isentropic, fluid=self.workingFluid)
                    if state_out_actual is not None:
                        state_out.copy_fromState(state_out_actual)

                # FIND state_in FROM state_out
                else:
                    if device.state_in.hasDefined('P') and state_out.hasDefined('P') and not device.state_in.hasDefined('T'):
                        print('\tReverse Isentropic Efficiency Calculation:\n\tstate_out: {0}\n\tstate_in: {1}'.format(state_out, device.state_in))
                        device.state_in.copy_fromState(self._get_state_in_from_state_out(device, state_out))

    def _add_pressureRatioRelation(self, device: WorkDevice):
        """Adds a linear equation describing the relation between end state pressures and the pressure ratio parameter of the work device.
        Works only with work devices that have one state_in and one states_out."""
        state_out = device.states_out[0]

        if isinstance(device, (Compressor, Pump)):  # Compression
            pressureRatioRelation_LHS = [((device, 'pressureRatio'), (device.state_in, 'P')), (-1, (state_out, 'P'))]
        else:
            assert isinstance(device, Turbine)  # Expansion
            pressureRatioRelation_LHS = [((device, 'pressureRatio'), (state_out, 'P')), (-1, (device.state_in, 'P'))]

        pressureRatioRelation = LinearEquation(LHS=pressureRatioRelation_LHS, RHS=0)
        device._pressureRatioRelationSetup = True

        if pressureRatioRelation.isSolvable():
            solution = pressureRatioRelation.solve()
            unknownAddress = list(solution.keys())[0]
            setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
            self._updatedUnknowns.add(unknownAddress)
        else:
            pressureRatioRelation.source = device
            self._equations.append(pressureRatioRelation)

    def _get_state_in_from_state_out(self, device: WorkDevice, state_out: StateIGas, percentDifference: float = 0.1, iteration_T_steps: float = 2):
        """Finds state_in to the WorkDevice by iterating and trying to match the isentropic efficiency."""
        # TODO: Can add the process for non-idealgases

        # Data Requirements:
        # state_out.P, state_in.P

        if isinstance(self.workingFluid, IdealGas):
            state_in_guess = StateIGas(P=device.state_in.P)
            apply_isentropicIGasProcess(constant_c=self.constant_c, state_in=state_in_guess, state_out=state_out, fluid=self.workingFluid)
            state_in_guess.clearFields(keepFields=['P', 'T'])  # Iteration guess state has only T and P defined.

            compression = state_out.P > device.state_in.P
            iteration = 1
            while True:
                print('_get_state_in_from_state_out: Solution iteration #{0} - state_in temperature guess: {1}'.format(iteration, state_in_guess.T))
                self.workingFluid.define(state_in_guess)
                state_out_ideal_guess = StateIGas(P=state_out.P)
                apply_isentropicIGasProcess(self.constant_c, fluid=self.workingFluid, state_in=state_in_guess, state_out=state_out_ideal_guess)

                if compression:
                    if not self.constant_c:
                        eta_isentropic_guess = (state_out_ideal_guess.h - state_in_guess.h) / (state_out.h - state_in_guess.h)
                    else:
                        eta_isentropic_guess = (state_out_ideal_guess.T - state_in_guess.T) / (state_out.T - state_in_guess.T)
                else:  # expansion
                    if not self.constant_c:
                        eta_isentropic_guess = (state_in_guess.h - state_out.h) / (state_in_guess.h - state_out_ideal_guess.h)
                    else:
                        eta_isentropic_guess = (state_in_guess.T - state_out.T) / (state_in_guess.T - state_out_ideal_guess.T)

                if isWithin(eta_isentropic_guess, percentDifference, '%', device.eta_isentropic):
                    print('_get_state_in_from_state_out: Solution satisfactory at iteration {0} - eta_isentropic Prescribed/Calculated: {1}/{2}\n\tstate_in: {3}'.format(iteration, device.eta_isentropic, eta_isentropic_guess, state_in_guess))
                    break
                else:
                    # Reset iteration guess state at each iteration to have T and P only.
                    state_in_guess = StateIGas(T=(state_in_guess.T - iteration_T_steps), P=device.state_in.P)  # reduce temperature by K/°C and try again to see if this is the right state_in that gives the prescribed isentropic efficiency
                    iteration += 1
            return state_in_guess

    def get_net_sWorkExtracted(self, returnExpression: bool = False):
        """Returns the value of the total specific work extracted by the WorkDevices of the flow. If returnExpression, returns the expression that gives the value when added in a LinearEquation."""
        self._net_sWorkExtracted = float('nan')
        expression_LHS = [ (-1, (self, '_net_sWorkExtracted')) ]

        for device in self.workDevices:
            stateBefore, stateAfter = self.get_surroundingItems(device, includeNone=True)  # returned list will have None values if there is no item in the spot before / after
            if stateBefore is None and isinstance(device, Turbine):
                stateBefore = device.state_in  # A turbine (commonly in steam cycles) may have multiple flows coming out of it. The state_in may not belong to the same flow as the state_out.
            if stateBefore is not None and stateAfter is not None:
                if not self.constant_c:
                    expression_LHS += [ (1, (stateBefore, 'h')) , (-1, (stateAfter, 'h')) ]  # effectively adds (h_in - h_out) to the equation
                else:  # constant c analysis
                    expression_LHS += [(1, (self.workingFluid.cp), (stateBefore, 'T')), (-1, (self.workingFluid.cp), (stateAfter, 'T'))]
            else:
                continue
        expression = LinearEquation(LHS=expression_LHS, RHS=0)  # -1 * self._net_sWorkExtracted + state_in.h - state_out.h = 0
        expression.source = 'Flows.get_net_sWorkExtracted'

        if expression.isSolvable():
            assert expression.get_unknowns()[0][0] == (self, '_net_sWorkExtracted')
            # Linear equation is solvable if only there is only one unknown. If there is only one unknown, it must be the self._net_sWorkExtracted since we know it is unknown for sure
            result = list(expression.solve().values())[0]
            return result
        else:
            if returnExpression:
                return expression.isolate( [(self, '_net_sWorkExtracted')] )
            else:
                return float('nan')

    def get_sHeatSupplied(self, returnExpression: bool = False):
        """Returns the value of the total specific heat supplied by the HeatDevices of the flow. If returnExpression, returns the expression that gives the value when added in a LinearEquation."""
        self._sHeatSupplied = float('nan')
        expression_LHS = [ (-1, (self, '_sHeatSupplied')) ]

        for device in set(device for device in self.heatDevices if isinstance(device, (Boiler, ReheatBoiler, Combustor, GasReheater) )):  # if not isinstance(device, HeatExchanger)
            expression_LHS += device.get_sHeatSuppliedExpression(forFlow=self, constant_c=self.constant_c)

        expression = LinearEquation(LHS=expression_LHS, RHS=0)
        expression.source = 'Flows.get_sHeatSupplied'

        if expression.isSolvable():
            assert expression.get_unknowns()[0][0] == (self, '_sHeatSupplied')
            # Linear equation is solvable if only there is only one unknown. If there is only one unknown, it must be the self._net_sWorkExtracted since we know it is unknown for sure
            result = list(expression.solve().values())[0]
            return result
        else:
            if returnExpression:
                return expression.isolate( [(self, '_sHeatSupplied')] )
            else:
                return float('nan')

    def __str__(self):
        """Returns the string representation of the Flow object."""
        toReturn = 'Flow@{0} - massFF:{1}, massFR:{2}'.format(id(self), self.massFF, self.massFR)
        return toReturn



