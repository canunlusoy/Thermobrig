
from typing import List, Dict
from itertools import combinations

from Models.Flows import Flow
from Models.Devices import Device, OpenFWHeater, ClosedFWHeater, MixingChamber, HeatExchanger
from Models.States import StatePure
from Utilities.PrgUtilities import findItem
from Utilities.Numeric import isNumeric, associatedPair

class Cycle:

    def __init__(self):

        self.flows: List[Flow] = []
        pass

    def solve(self):

        for flow in self.flows:
            flow.solve()

        intersections = self._identify_intersections()

        for device in intersections:
            print('Solving intersection: {0}'.format(device))
            self._solveIntersection(device)

    def _identify_intersections(self):
        """First / last devices in flow items lists are checked if they appear in multiple flows' items lists. If so, they are inferred to be intersections, i.e. points where flows diverge or combine."""
        intersections, endPoints = set(), set()

        # Find connection points, i.e. where flows merge or diverge
        for flow in self.flows:
            for endPoint in [flow.items[0], flow.items[-1]]:
                if isinstance(endPoint, Device):
                    if endPoint not in endPoints:
                        endPoints.add(endPoint)
                    else:
                        intersections.add(endPoint)

        # Find cross-overs, i.e. where flows interact without mixing, e.g. in heat exchangers
        for flow, otherFlow in list(combinations(self.flows, 2)):
            for flow_device in flow.devices:

                # if the same device appears also in the other flow, and if the states surrounding the same device are different in both flows
                if flow_device in otherFlow.devices and all(item not in otherFlow.get_surroundingItems(flow_device) for item in flow.get_surroundingItems(flow_device)):
                    intersections.add(flow_device)

                # if the flow device has a parent device, and the same parent is the parent of another device in the other flow
                if flow_device.parentDevice is not None and any(otherFlow_device.parentDevice is flow_device.parentDevice for otherFlow_device in otherFlow.devices):
                    intersections.add(flow_device.parentDevice)

        return intersections

    def _solveIntersection(self, device: Device):

        if isinstance(device, ClosedFWHeater):

            cFWH_heatExchanger = HeatExchanger()

            for bundle in device.bundles:
                bundle_mixingChamber = MixingChamber()
                bundle_mixingChamber.states_in = bundle.states_in

                self.solve_mixingChamber(bundle_mixingChamber)

                cFWH_heatExchanger.lines.append([bundle_mixingChamber.state_out, bundle.state_out])

            self.solve_heatExchanger(cFWH_heatExchanger)

        elif isinstance(device, MixingChamber):
            self.solve_mixingChamber(device)


    def _find_flows_of_states(self, states: List[StatePure]) -> Dict[Flow, StatePure]:
        """Returns a dictionary mapping provided states to the flows which they belong."""
        flow_state_dict = {}
        for state in states:
            for flow in self.flows:
                if state in flow.items:  # assumes one state_in to the mixing chamber is associated only with one flow
                    flow_state_dict.update({flow: state})
        return flow_state_dict

    def _find_flow_of_state(self, state: StatePure) -> Flow:
        for flow in self.flows:
            if state in flow.items:  # assumes one state_in to the mixing chamber is associated only with one flow
                return flow



    def solve_heatExchanger(self, device: HeatExchanger):

        for line_state_in, line_state_out in device:


            pass


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

            state_no_h = findItem(endStates, lambda state: not isNumeric('h'))

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

    def find_divergencePoints(self):

        flow_items_dict = {flow: flow.items for flow in self.flows}

        for flow in self.flows:
            otherFlows = [otherFlow for otherFlow in self.flows if otherFlow is not flow]

            for otherFlow in otherFlows:
                if otherFlow.states[0] in flow.states:
                    print('{0} diverges from {1}'.format(otherFlow, flow))









        # find flow intersections
        # solve mixing chambers