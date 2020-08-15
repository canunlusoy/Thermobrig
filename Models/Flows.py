
from math import exp
from operator import itemgetter
from typing import Union, List, Dict

from Methods.ThprOps import apply_isentropicEfficiency, apply_incompressibleWorkRelation

from Models.States import StatePure, StateIGas
from Models.Fluids import Fluid, IdealGas
from Models.Devices import Device, WorkDevice, HeatDevice, Boiler, Combustor, MixingChamber, OpenFWHeater, Trap

from Utilities.Numeric import isNumeric, isWithin
from Utilities.PrgUtilities import twoList
from Utilities.Exceptions import DataVerificationError

# FLOWS include relations between states (same T / P / h / s)
# CYCLES include relations between flows (mass fractions, energy transfers)

class Flow:

    def __init__(self, workingFluid: Fluid, massFlowRate: float = float('nan'), massFlowFraction: float = float('nan'), calculate_h_forIncompressibles: bool = False):

        # Not considering flows with multiple fluids, one flow can contain only one fluid
        self.workingFluid = workingFluid
        self.massFR = massFlowRate
        self.massFF = massFlowFraction


        self.items = []
        # Items is a list of devices and states making up the flow.
        # If flow is cyclic, items list should start with a state and end with the same state.

        self._calculate_h_forIncompressibles = calculate_h_forIncompressibles

        self._initialSolutionComplete = False
        self._equations = []

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

    def isFullyDefined(self):
        """Checks if all states in the flow are fully defined."""
        return all(state.isFullyDefined() for state in self.states)

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

    def solve(self):
        self._define_definableStates()

        if not self._initialSolutionComplete:
            self._set_devices_endStateReferences()

            for device in self.devices:
                print('Solving device: {0}'.format(device))
                self._solveDevice(device)

            self._define_definableStates()

        get_undefinedStates = lambda: [state for state in self.states if not state.isFullyDefined()]
        undefinedStates_previousIteration = []
        iterationCounter = 0
        while (undefinedStates := get_undefinedStates()) != undefinedStates_previousIteration:
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

        if not self._initialSolutionComplete:
            self._initialSolutionComplete = True

    def _define_definableStates(self) -> None:
        """Runs the appropriate defFcn (function to fully define the state properties) for states which can be fully defined, i.e. has 2+ independent intensive properties defined."""
        self._defineStates_ifDefinable(self.states)

    def _defineStates_ifDefinable(self, states: Union[StatePure, List, twoList]):
        if isinstance(states, StatePure):
            states = [states]
        for state in states:
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

        if not self._initialSolutionComplete:  # the below processes do not need to be done in each flow solution iteration, but only for the initial one

            if isinstance(device, HeatDevice):
                # Setting end state pressures along the same line if pressures is assumed constant along each line
                if device._infer_constant_linePressures:
                    device.infer_constant_linePressures()
                # Setting up fixed exit temperature if inferring exit temperature from one exit state
                if device._infer_fixed_exitT:
                    device.infer_fixed_exitT()

            if isinstance(device, MixingChamber):
                # Setting pressures of all in / out flows to the same value
                if device._infer_common_mixingPressure:
                    device.infer_common_mixingPressure()

            if isinstance(device, Trap):
                if device._infer_constant_enthalpy:
                    device.infer_constant_enthalpy()

        self._defineStates_ifDefinable(endStates)

    def solve_workDevice(self, device: WorkDevice):
        """Determines outlet state based on available inlet state using isentropic efficiency."""
        # Find the state_out out of the device IN THIS FLOW - work devices may have multiple states_out (e.g. turbines with many extractions for reheat, regeneration).

        occurrences_ofDevice = [index for index, item in enumerate(self.items) if item is device]
        states_afterDevice: List[StatePure] = [self.items[index + 1] for index in occurrences_ofDevice]  # state_afterDevice is a StatePure for sure after the check in _check_itemsConsistency

        for state_out in states_afterDevice:
            if device.state_in.hasDefined('s') and device.state_in.hasDefined('h') and state_out.hasDefined('P'):

                # going to overwrite state_out - TODO: Need to copy in the first time, then verify in subseqs
                state_out.copy_fromState(apply_isentropicEfficiency(state_in=device.state_in,
                                                                    state_out_ideal=state_out,
                                                                    eta_isentropic=device.eta_isentropic,
                                                                    fluid=self.workingFluid))
                # assert state_out.isFullyDefined()

            # if self._calculate_h_forIncompressibles and device.state_in.x <= 0 and device.state_in.hasDefined('P'):
            #     apply_incompressibleWorkRelation(device.state_in, state_out)

                # # overwrite h with calculated value
                # state_out.h = device.state_in.h + device.state_in.mu * (state_out.P - device.state_in.P)  # W = integral(mu * dP) for reversible steady flow work, mu is constant for incompressibles

    @property
    def net_sWorkExtracted(self):
        total_sWorkExtracted = 0
        for device in self.workDevices:
            stateBefore, stateAfter = self.get_surroundingItems(device)
            total_sWorkExtracted += stateBefore.h - stateAfter.h
        return total_sWorkExtracted

    @property
    def sHeatSupplied(self):
        total_sHeatSupplied = 0
        for device in set(self.heatDevices):  # Important! Boilers etc. may be listed twice if flow is reheated. A single total_sHeatSupplied of a HeatDevice includes heat supplied in all passes!
            total_sHeatSupplied += device.total_sHeatSupplied
        return total_sHeatSupplied


class IdealGasFlow(Flow):

    def __init__(self, workingFluid: IdealGas):
        super(IdealGasFlow, self).__init__(workingFluid)

    def get_P_r(self, state: StateIGas):
        assert isNumeric(state.s0)
        return exp(state.s0 / self.workingFluid.R)

    def get_mu_R(self, state: StateIGas):
        assert isNumeric(state.T)
        return state.T / self.get_P_r(state)


