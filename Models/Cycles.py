
from typing import List, Dict, Set
from itertools import combinations

from Models.Flows import Flow
from Models.Devices import Device, OpenFWHeater, ClosedFWHeater, MixingChamber, HeatExchanger
from Models.States import StatePure
from Utilities.PrgUtilities import findItem
from Utilities.Numeric import isNumeric

class Cycle:

    def __init__(self, infer_mainLine: bool = True):

        self.flows: List[Flow] = []

        self._infer_mainLine = infer_mainLine
        pass

    def solve(self):

        if self._infer_mainLine:
            if all(not flow.massFF == 1 for flow in self.flows):  # if any flow already has its mass flow fraction defined as 1, it is the mainLine, don't try to infer any
                self.infer_mainLine()

        self._add_flowReferences_toStates()

        for flow in self.flows:
            flow.solve()

        if not all(flow.isFullyDefined() for flow in self.flows):
            intersections = self._identify_intersections()
            for device in intersections:
                self._solveIntersection(device)

    def _add_flowReferences_toStates(self):
        """Adds a 'flow' attribute to all the state objects in all flows included in the cycle. """
        # Not a big fan of doing this - states are a lower level entity than flows and should not have access to the higher level entity which contains it.
        # Instead, they should be accessed from the flows which contain them. But had to resort to this for convenience.
        for flow in self.flows:
            for state in flow.states:
                setattr(state, 'flow', flow)

    def _identify_intersections(self):
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
            flow_itemSet, otherFlow_itemSet = set(flow.items[1:-1]), set(otherFlow.items[1:-1])  # [1:-1] not to include endPoints, as their intersections are covered by above process
            intersections.add(item for item in flow_itemSet.intersection(otherFlow_itemSet) if isinstance(item, Device))  # add *devices* encountered in both flows

        return intersections

    def infer_mainLine(self):

        if len(self.flows) == 1:
            # If there is only one flow, it has all the mass flowing through it. This flow may or may not be a cycle!
            self.flows[0].set_or_verify({'massFF': 1})
        else:
            raise NotImplementedError

    def _solveIntersection(self, device: Device):

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

        # Mixing chambers have multiple in flows and one out flow
        endStates = list(device.states_in) + [device.state_out]

        # Each end state is assumed to belong to a different flow
        flows_states = self._find_flows_of_states(endStates)
        outflow = self._find_flow_of_state(device.state_out)

        # Heat balance
        number_ofUnknownMassFF = sum(1 for flow in flows_states.keys() if not isNumeric(flow.massFF))
        number_ofUnknownEnthalpies = sum(1 for flow in flows_states.keys() if not isNumeric(flows_states[flow].h))

        # m1h1 + m2h2 + m3h3 = m4h4

        # Need to solve for enthalpy
        if number_ofUnknownEnthalpies <= 1 and number_ofUnknownMassFF == 0:

            state_no_h = findItem(endStates, lambda state: not isNumeric(state.h))

            if state_no_h is device.state_out:
                device.state_out.h = (sum(flow.massFF * state.h for flow, state in flows_states.items())) / outflow.massFF
            else:
                state_no_h.h = (outflow.massFF * device.state_out.h - (sum(flow.massFF * state.h for flow, state in flows_states.items() if state is not state_no_h and state is not device.state_out))) / (self._find_flow_of_state(state_no_h).massFF)

        # Need to solve for missing mass flow fraction
        elif number_ofUnknownMassFF <= 1 and number_ofUnknownEnthalpies == 0:

            flow_no_MFF = findItem(flows_states.keys(), lambda flow: not isNumeric(flow.massFF))

            if flow_no_MFF is outflow:
                outflow.massFF = sum(flow.massFF * state.h for flow, state in flows_states.items() if flow is not outflow) / device.state_out.h
                assert outflow.massFF == sum(flow.massFF for flow in flows_states.keys() if flow is not outflow)
            else:
                flow_no_MFF.massFF = (outflow.massFF * device.state_out.h - sum(flow.massFF * state.h for flow, state in flows_states.items() if state is not device.state_out and state is not flows_states[flow_no_MFF])) / flows_states[flow_no_MFF].h
                assert flow_no_MFF.massFF == outflow.massFF - sum(flow.massFF for flow in flows_states.keys() if flow is not outflow and flow is not flow_no_MFF)


