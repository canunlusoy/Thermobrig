
from math import exp
from operator import itemgetter
from typing import Union, List

from Methods.ThprOps import get_state_out_actual

from Models.States import StatePure, StateIGas
from Models.Fluids import Fluid, IdealGas
from Models.Devices import Device, WorkDevice, HeatDevice, Boiler, Combustor

from Utilities.Numeric import isNumeric, isWithin, twoList
from Utilities.Exceptions import DataVerificationError

# FLOWS include relations between states (same T / P / h / s)
# CYCLES include relations between flows (mass fractions, energy transfers)

class Flow:

    def __init__(self, workingFluid: Fluid, massFlowRate: float = float('nan'), massFlowFraction: float = float('nan')):

        # Not considering flows with multiple fluids, one flow can contain only one fluid
        self.workingFluid = workingFluid
        self.massFlowRate = massFlowRate
        self.massFlowFraction = massFlowFraction


        self.items = []

        self.stateRelations = {}


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
        indices_states, indices_devices = [], []
        for index, item in enumerate(self.items):
            if isinstance(item, StatePure):
                indices_states.append(index)
            elif isinstance(item, Device):
                indices_devices.append(index)

        # todo check every second item is a state
        for stateIndex in indices_states:
            # Check if every state is followed by a device
            assert (stateIndex + 1) in indices_devices

    def _set_devices_stateReferences(self):
        self._check_itemsConsistency()

        # TODO: Devices with flow going in and out multiple times! State references!

        def core():
            for itemIndex, item in enumerate(self.items):
                if isinstance(item, Device):
                    item.set_states(state_in=self.items[itemIndex - 1], state_out=self.items[itemIndex + 1])

        if isinstance(self.items[0], Device):
            assert isinstance(self.items[-1], StatePure)
            self.items.insert(0, self.items[-1])
            core()
            self.items.pop(0)

        elif isinstance(self.items[-1], Device):
            assert isinstance(self.items[0], StatePure)
            self.items.append(self.items[0])
            core()
            self.items.pop(-1)

    def _define_definableStates(self) -> None:
        """Runs the appropriate defFcn (function to fully define the state properties) for states which can be fully defined, i.e. has 2+ independent intensive properties defined."""
        self._define_ifDefinable(self.states)

    def _define_ifDefinable(self, states: Union[StatePure, List, twoList]):
        if isinstance(states, StatePure):
            states = [states]
        for state in states:
            if not state.isFullyDefined() and state.isFullyDefinable():
                state.copy_fromState(self.workingFluid.define(state))

    def _solveDevice(self, device: Device):
        endStates: twoList[StatePure] = twoList([device.state_in, device.state_out])

        if isinstance(device, WorkDevice):

            # Actual outlet state determination from ideal outlet state - has to be here, need to know fluid to define state
            if device.eta_isentropic != 1:
                if device.state_in.isFullyDefined() and device.state_out.hasDefined('P'):
                    # going to overwrite state_out
                    device.state_out.copy_fromState(get_state_out_actual(state_in=device.state_in,
                                                                         state_out_ideal=device.state_out,  # uses only the P information from available state_out
                                                                         eta_isentropic=device.eta_isentropic,
                                                                         fluid=self.workingFluid))
                    assert device.state_out.isFullyDefined()

        if isinstance(device, HeatDevice):

            # Setting end state pressures along the same line if pressures is assumed constant along each line
            if device._infer_constant_linePressures:
                device.infer_constant_linePressures()

            # Setting up fixed exit temperature if inferring exit temperature from one exit state
            if device._infer_fixed_exitT:
                device.infer_fixed_exitT()

        self._define_ifDefinable(endStates)

    def solve(self):
        self._define_definableStates()
        self._set_devices_stateReferences()

        for device in self.devices:
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
                self._define_ifDefinable(state)

    @property
    def net_sWorkExtracted(self):
        total_sWorkExtracted = 0
        for device in self.workDevices:
            total_sWorkExtracted += device.sWorkExtracted
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


