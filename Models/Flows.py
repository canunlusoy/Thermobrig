
from math import exp
from operator import itemgetter
from typing import Union, List

from Methods.ThprOps import get_state_out_actual

from Models.States import StatePure, StateIGas
from Models.Fluids import Fluid, IdealGas
from Models.Devices import Device, WorkDevice, HeatDevice, Boiler, Combustor

from Utilities.Numeric import isNumeric, isWithin
from Utilities.Exceptions import DataVerificationError

# FLOWS include relations between states (same T / P / h / s)
# CYCLES include relations between flows (mass fractions, energy transfers)

class Flow:

    def __init__(self, workingFluid: Fluid):

        # Not considering flows with multiple fluids, one flow can contain only one fluid
        self.workingFluid = workingFluid

        self.items = []

        self.stateRelations = {}


    @property
    def states(self):
        return [item for item in self.items if isinstance(item, StatePure)]

    @property
    def devices(self):
        return [item for item in self.items if isinstance(item, Device)]

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
        for state in self.states:
            if state.isFullyDefinable() and not state.isFullyDefined():
                state.copy_fromState(self.workingFluid.define(state))

    def solve(self):
        self._define_definableStates()
        self._set_devices_stateReferences()

        # Evaluate relations and constraints

        device_solved = {device: False for device in self.devices}

        for device in self.devices:
            endStates = [device.state_in, device.state_out]


            if isinstance(device, WorkDevice):

                # Actual outlet state determination from ideal outlet state
                if device.eta_isentropic != 1:
                    if device.state_in.isFullyDefined() and device.state_out.hasDefined('P'):
                        # going to overwrite state_out
                        device.state_out.copy_fromState(get_state_out_actual(state_in=device.state_in,
                                                                             state_out_ideal=device.state_out,  # uses only the P information from available state_out
                                                                             eta_isentropic=device.eta_isentropic,
                                                                             fluid=self.workingFluid))
                        assert device.state_out.isFullyDefined()

            if isinstance(device, HeatDevice):

                # Setting end state pressures if constant operating pressure is assumed
                if device.infer_constant_operatingP:
                    endStates_Pvals = [(state, isNumeric(getattr(state, 'P'))) for state in endStates]
                    # if both end states have a P defined, ensure they match within reasonable tolerance
                    if (number_ofNumericPvals := sum(1 for row in endStates_Pvals if row[1] == True)) == 2:
                        assert isWithin(device.state_in.P, 3, '%', device.state_out.P)
                    # if only one end state has a P defined, apply it to the other end state
                    elif number_ofNumericPvals == 1:
                        endStates_Pvals.sort(key=itemgetter(1))  # sort by truth of isNumeric
                        state_withNonNumericPval = endStates_Pvals[0][0]
                        state_withNonNumericPval.P = endStates_Pvals[1][0].P

                # Setting up fixed exit temperature if inferring exit temperature from one exit state
                if device.infer_fixed_exitT:
                    if device.state_out.hasDefined('T'):
                        device.set_or_verify({'T_exit_fixed': device.state_out.T})
                        device.state_out.set_or_verify({'T': device.T_exit_fixed})

            if all(state.isFullyDefined() for state in endStates):
                device_solved[device] = True


        self._define_definableStates()




class IdealGasFlow(Flow):

    def __init__(self, workingFluid: IdealGas):
        super(IdealGasFlow, self).__init__(workingFluid)





    def get_P_r(self, state: StateIGas):
        assert isNumeric(state.s0)
        return exp(state.s0 / self.workingFluid.R)

    def get_mu_R(self, state: StateIGas):
        assert isNumeric(state.T)
        return state.T / self.get_P_r(state)


