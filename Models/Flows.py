
from math import exp
from typing import Union, List

from Models.States import StatePure, StateIGas
from Models.Fluids import Fluid, IdealGas
from Models.Devices import Device, WorkDevice, HeatDevice
from Utilities.Numeric import isNumeric

# FLOWS include relations between states (same T / P / h / s)
# CYCLES include relations between flows (mass fractions, energy transfers)

class Flow:

    def __init__(self, workingFluid: Fluid):

        self.workingFluid = workingFluid


        # Not considering flows with multiple fluids, one flow can contain only one fluid
        self.items = []

        self.stateRelations = {}


    @property
    def states(self):
        return [item for item in self.items if isinstance(item, StatePure)]

    @property
    def devices(self):
        return [item for item in self.items if isinstance(item, Device)]

    def check_itemsConsistency(self):
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

    def set_devices_stateReferences(self):

        self.check_itemsConsistency()

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

    def solve(self):
        self.fullyDefine_definableStates()

        # Evaluate relations and constraints

        for device in self.devices:
            if isinstance(device, WorkDevice):





        self.fullyDefine_definableStates()

    def fullyDefine_definableStates(self) -> None:
        """Runs the appropriate defFcn (function to fully define the state properties) for states which can be fully defined, i.e. has 2+ independent intensive properties defined."""
        for state in self.states:
            if state.isFullyDefinable() and not state.isFullyDefined():
                state.copy_fromState(self.workingFluid.defFcn(state, mpDF=self.workingFluid.mpDF))
                # TODO - check if state is correctly overwritten


class IdealGasFlow(Flow):

    def __init__(self, workingFluid: IdealGas):
        super(IdealGasFlow, self).__init__(workingFluid)





    def get_P_r(self, state: StateIGas):
        assert isNumeric(state.s0)
        return exp(state.s0 / self.workingFluid.R)

    def get_mu_R(self, state: StateIGas):
        assert isNumeric(state.T)
        return state.T / self.get_P_r(state)


