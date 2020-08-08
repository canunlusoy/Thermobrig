
from typing import List, Dict, Set
from itertools import combinations

from Models.Flows import Flow
from Models.Devices import Device, OpenFWHeater, ClosedFWHeater, MixingChamber, HeatExchanger
from Models.States import StatePure
from Utilities.Numeric import isNumeric
from Utilities.PrgUtilities import LinearEquation

class Cycle:

    def __init__(self):
        self.flows: List[Flow] = []

    def solve(self):

        self._add_flowReferences_toStates()
        intersections = self._get_intersections()

        iterationCounter = 0
        while iterationCounter < 5:

            for flow in self.flows:
                flow.solve()

            if not all(flow.isFullyDefined() for flow in self.flows):
                for device in intersections:
                    self._solveIntersection(device)

            iterationCounter += 1

    def _add_flowReferences_toStates(self):
        """Adds a 'flow' attribute to all the state objects in all flows included in the cycle. """
        # Not a big fan of doing this - states are a lower level entity than flows and should not have access to the higher level entity which contains it.
        # Instead, they should be accessed from the flows which contain them. But had to resort to this for convenience.
        for flow in self.flows:
            for state in flow.states:
                setattr(state, 'flow', flow)

    def _get_intersections(self):
        """Iterates through flows' items to find intersections. Specifically, checks for shared endpoints and devices."""

        endPoints = []
        intersections = set()

        # Identify end connections - DEVICES
        for flow in self.flows:
            for endPoint in [flow.items[0], flow.items[-1]]:
                if isinstance(endPoint, Device):  # endPoint may be a state or a device! - pick devices
                    if endPoint not in endPoints:
                        endPoints.append((endPoint, flow))
                    else:
                        # this endPoint of this flow is already registered as an endPoint, likely by some other flow,
                        # or by the same flow in the previous iteration of the inner for loop in case of a cyclic flow.
                        intersections.add(endPoint)

        # Identify crossover points - DEVICES
        for flow, otherFlow in combinations(self.flows, 2):
            flow_itemSet, otherFlow_itemSet = set(item for item in flow.items[1:-1] if isinstance(item, Device)), set(item for item in otherFlow.items[1:-1] if isinstance(item, Device))
            # [1:-1] not to include endPoints, as their intersections are covered by above process
            intersections.update(item for item in flow_itemSet.intersection(otherFlow_itemSet) if isinstance(item, Device))  # add *devices* encountered in both flows

        return intersections

    def _solveIntersection(self, device: Device):
        """Wrapper for various device solution methods. These methods need to be used in the cycle scope as they require information of interacting flows."""

        if isinstance(device, HeatExchanger):
            self.solve_heatExchanger(device)

        elif isinstance(device, MixingChamber):
            self.solve_mixingChamber(device)

    def solve_heatExchanger(self, device: HeatExchanger):
        """Does a heat balance over the flows entering and exiting the heat exchanger, calculates the missing property and sets its value in the relevant object."""

        # m1h11 + m2h21 + m3h31 = m1h12 + m2h22 + m3h32

        # Cases:
        # [1] One mass flow fraction is unknown
        # [2] One specific enthalpy is unknown

        lines_withUnknown_massFF, states_withUnknown_enthalpies = [], []
        for line in device.lines:
            if not isNumeric(line[0].flow.massFF):  # check if the flow of the first endState of the line (state_in of line) has numeric massFF
                lines_withUnknown_massFF.append(line)
            for endState_index, line_endState in enumerate(line):
                if not isNumeric(line_endState.h):
                    states_withUnknown_enthalpies.append((endState_index, line_endState))

        number_of_unknown_massFFs = len(lines_withUnknown_massFF)
        number_of_unknown_enthalpies = len(states_withUnknown_enthalpies)

        # Case [1]
        if number_of_unknown_massFFs == 1 and number_of_unknown_enthalpies == 0:
            line_withUnknown_massFF = lines_withUnknown_massFF[0]

            sum_sideA = 0
            for line_state_in, line_state_out in [line for line in device.lines if line is not line_withUnknown_massFF]:
                line_massFF = line_state_in.flow.massFF
                sum_sideA += (line_massFF * (line_state_in.h - line_state_out.h))

            delta_h_sideB = line_withUnknown_massFF[1].h - line_withUnknown_massFF[0].h
            line_withUnknown_massFF[0].flow.massFF = (sum_sideA / delta_h_sideB)

        # Case [2]
        elif number_of_unknown_massFFs == 0 and number_of_unknown_enthalpies == 1:
            endState_index, state_withUnknown_enthalpy = states_withUnknown_enthalpies[0]

            # Side A is the side of the heat balance with the unknown enthalpy, Side B is the one with all terms known.
            fullyDefinedStates_ofSideA = [line[endState_index] for line in device.lines if line[endState_index] is not state_withUnknown_enthalpy]
            states_ofSideB = [line[endState_index - 1] for line in device.lines]

            H_tot_sideB = sum(state.flow.massFF * state.h for state in states_ofSideB)
            known_H_tot_sideA = sum(state.flow.massFF * state.h for state in fullyDefinedStates_ofSideA)
            state_withUnknown_enthalpy.h = (H_tot_sideB - known_H_tot_sideA) / state_withUnknown_enthalpy.flow.massFF







    def solve_mixingChamber(self, device: MixingChamber):

        # m1h1 + m2h2 + m3h3 = m4h4

        # Cases:
        # [1] One specific enthalpy is unknown
        # [2] One mass flow fraction is unknown

        # m1 + m2 + m3 - m4 = 0
        massBalance = LinearEquation([[(state.flow.massFF) for state in device.states_in] + [-1 * device.state_out.flow.massFF], 0])
        if massBalance.isSolvable():
            unknown_massFF, solution = massBalance.solve()
            unknown_massFF = solution

        # m1h1 + m2h2 + m3h3 - m4h4 = 0
        heatBalance = LinearEquation([[(state.flow.massFF * state.h) for state in device.states_in] + [device.state_out.flow.massFF * device.state_out.h], 0])
        if heatBalance.isSolvable():
            unknown_variable, solution = heatBalance.solve()
            unknown_variable = solution

        states_withUnknown_enthalpy, states_withUnknown_flow_massFF = [], []
        for endState in device.endStates:
            if not isNumeric(endState.flow.massFF):
                states_withUnknown_flow_massFF.append(endState)
            if not isNumeric(endState.h):
                states_withUnknown_enthalpy.append(endState)

        number_of_unknown_massFFs = len(states_withUnknown_flow_massFF)
        number_of_unknown_enthalpies = len(states_withUnknown_enthalpy)

        # Case [1] - Need to solve for enthalpy
        if number_of_unknown_enthalpies == 1 and number_of_unknown_massFFs == 0:

            state_no_enthalpy = states_withUnknown_enthalpy[0]

            if state_no_enthalpy is device.state_out:
                state_no_enthalpy.h = (sum(state.flow.massFF * state.h for state in device.endStates if state is not state_no_enthalpy)) / state_no_enthalpy.flow.massFF
            else:
                state_no_enthalpy.h = (device.state_out.flow.massFF * device.state_out.h - (sum(state.flow.massFF * state.h for state in device.endStates if state is not state_no_enthalpy and state is not device.state_out))) / (state_no_enthalpy.flow.massFF)

        # Case [2] - Need to solve for missing mass flow fraction
        elif number_of_unknown_massFFs == 1 and number_of_unknown_enthalpies == 0:

            state_no_flow_massFF = states_withUnknown_flow_massFF[0]

            if state_no_flow_massFF is device.state_out:
                # Mass balance
                state_no_flow_massFF.flow.massFF = sum(state.flow.massFF for state in device.states_in)
                # Verify with heat balance
                assert state_no_flow_massFF.flow.massFF == sum(state.flow.massFF * state.h for state in device.endStates if state is not device.state_out) / device.state_out.h
            else:
                # Mass balance
                state_no_flow_massFF.flow.massFF = device.state_out.flow.massFF - sum(state.flow.massFF for state in device.states_in if state is not state_no_flow_massFF)
                # Verify with heat balance
                assert state_no_flow_massFF.flow.massFF == (device.state_out.flow.massFF * device.state_out.h - sum(state.flow.massFF * state.h for state in device.states_in if state is not state_no_flow_massFF)) / state_no_flow_massFF.h
