
from math import exp
from operator import itemgetter
from typing import Union, List

from Methods.ThprOps import get_state_out_actual

from Models.States import StatePure, StateIGas
from Models.Fluids import Fluid, IdealGas
from Models.Devices import Device, WorkDevice, HeatDevice, Boiler, Combustor, MixingChamber, OpenFWHeater, Trap

from Utilities.Numeric import isNumeric, isWithin, twoList
from Utilities.Exceptions import DataVerificationError

# FLOWS include relations between states (same T / P / h / s)
# CYCLES include relations between flows (mass fractions, energy transfers)

class Flow:

    def __init__(self, workingFluid: Fluid, massFlowRate: float = float('nan'), massFlowFraction: float = float('nan')):

        # Not considering flows with multiple fluids, one flow can contain only one fluid
        self.workingFluid = workingFluid
        self.massFlowFraction = massFlowFraction


        self.items = []
        # Items is a list of devices and states making up the flow.
        # If flow is cyclic, items list should start with a state and end with the same state.


    @property
    def states(self):
        return [item for item in self.items if isinstance(item, StatePure)]

    @property
    def devices(self):
        return [item for item in self.items if isinstance(item, Device)]

    @property
    def workDevices(self):
        return [item for item in self.items if isinstance(item, WorkDevice)]

    @property
    def heatDevices(self):
        return [item for item in self.items if isinstance(item, HeatDevice)]

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

    def _set_devices_stateReferences(self):
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

    def _define_definableStates(self) -> None:
        """Runs the appropriate defFcn (function to fully define the state properties) for states which can be fully defined, i.e. has 2+ independent intensive properties defined."""
        self._defineStates_ifDefinable(self.states)

    def _defineStates_ifDefinable(self, states: Union[StatePure, List, twoList]):
        if isinstance(states, StatePure):
            states = [states]
        for state in states:
            if not state.isFullyDefined() and state.isFullyDefinable():
                state.copy_fromState(self.workingFluid.define(state))

    def _solveDevice(self, device: Device):
        endStates = device.endStates

        if isinstance(device, WorkDevice):

            # Actual outlet state determination from ideal outlet state - has to be here, need to know fluid to define state

            for current_state_out in device.states_out:
                # Work devices may have multiple outlets with flows of different pressure. Repeat process for each state_out.
                if device.state_in.isFullyDefined() and current_state_out.hasDefined('P'):
                    # going to overwrite state_out
                    current_state_out.copy_fromState(get_state_out_actual(state_in=device.state_in,
                                                                          state_out_ideal=current_state_out,  # uses only the P information from available state_out
                                                                          eta_isentropic=device.eta_isentropic,
                                                                          fluid=self.workingFluid))
                    assert current_state_out.isFullyDefined()

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

            # Heat balance needs mass fractions of multiple input flows. This must be done at cycle scope.

        if isinstance(device, Trap):
            if device._infer_constant_enthalpy:
                device.infer_constant_enthalpy()

        self._defineStates_ifDefinable(endStates)

    def solve(self):
        self._define_definableStates()
        self._set_devices_stateReferences()

        for device in self.devices:
            print('Solving device: {0}'.format(device))
            self._solveDevice(device)

        self._define_definableStates()

        get_undefinedStates = lambda: [state for state in self.states if not state.isFullyDefined()]
        iterationCounter = 0
        while (undefinedStates := get_undefinedStates()) != []:
            iterationCounter += 1
            print('Flow solution iteration #{0}'.format(iterationCounter))
            for state in undefinedStates:
                stateIndex = self.items.index(state)
                surroundingDevices = [self.items[stateIndex - 1], self.items[stateIndex + 1]]
                for device in surroundingDevices:
                    if not state.isFullyDefined():  # the state may become defined in first iteration of loop
                        self._solveDevice(device)
                self._defineStates_ifDefinable(state)

    @property
    def net_sWorkExtracted(self):
        total_sWorkExtracted = 0
        for device in self.workDevices:

            deviceIndex_inFlow = self.items.index(device)
            stateBefore = self.items[deviceIndex_inFlow - 1]
            stateAfter = self.items[deviceIndex_inFlow + 1]
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


