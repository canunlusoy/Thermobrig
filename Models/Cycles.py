
from typing import List, Dict, Set
from itertools import combinations

from Models.Flows import Flow
from Models.Devices import Device, OpenFWHeater, ClosedFWHeater, MixingChamber, HeatExchanger, Turbine
from Models.States import StatePure, FlowPoint
from Utilities.Numeric import isNumeric
from Utilities.PrgUtilities import LinearEquation, System_ofLinearEquations, setattr_fromAddress


class Cycle:

    def __init__(self):
        self.flows: List[Flow] = []
        self.netPower = float('nan')
        self._equations: List[LinearEquation] = []
        self._initialSolutionComplete = False

    def updateEquations(self):
        for equation in self._equations:
            if any(unknown in equation.get_unknowns() for unknown in self._updatedUnknowns):
                equation.update()
            self._updatedUnknowns = []

    def solve(self):

        # Steps for initialization
        if not self._initialSolutionComplete:
            self._convertStates_toFlowPoints()

            # 2 separate loops - device endStates may be from different flows. First set endState references, then work on each device for each flow they are in.
            for flow in self.flows:
                flow._set_devices_endStateReferences()
            for flow in self.flows:
                flow.solve()

            # Identify areas where flows interact, e.g. heat exchangers or flow connections
            intersections = self._get_intersections()
            if not all(flow.isFullyDefined() for flow in self.flows):
                for device in intersections:
                    self._solveIntersection(device)

            self._add_netPowerBalance()
            self._resolve_massFlows()

            self._initialSolutionComplete = True

        for flow in self.flows:
            flow.solve()

        self._updatedUnknowns = []

        solvedEquations = []
        for equation in self._equations:
            equation.update()
            if equation.isSolvable():
                solution = equation.solve()
                unknownAddress = list(solution.keys())[0]
                setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
                self._updatedUnknowns.append(unknownAddress)
                solvedEquations.append(equation)

        for equation in solvedEquations:
            self._equations.remove(equation)
        solvedEquations = []

        self.updateEquations()

        for equation1, equation2 in combinations(self._equations, 2):
            if (system := System_ofLinearEquations([equation1, equation2])).isSolvable():
                solution = system.solve()
                unknownAddresses = list(solution.keys())
                for unknownAddress in unknownAddresses:
                    setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
                    self._updatedUnknowns.append(unknownAddress)
                solvedEquations += [equation1, equation2]

        for equation in solvedEquations:
            try:
                self._equations.remove(equation)
            except ValueError:
                pass
        solvedEquations = []

        self.updateEquations()

        for equation1, equation2, equation3 in combinations(self._equations, 3):
            if (system := System_ofLinearEquations([equation1, equation2, equation3])).isSolvable():
                solution = system.solve()
                unknownAddresses = list(solution.keys())
                for unknownAddress in unknownAddresses:
                    setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
                    self._updatedUnknowns.append(unknownAddress)
                solvedEquations += [equation1, equation2, equation3]

        for equation in solvedEquations:
            self._equations.remove(equation)
        solvedEquations = []

        self.updateEquations()

    def _solve_combination_ofEquations(self, number_ofEquations: int):
        """Iterates through combinations of equations (from the _equations pool) with the specified number_ofEquations. For each combination, checks if the
        system is solvable. If so, solves it, assigns the unknowns the solution values and removes the solved equations from the _equations pool."""
        for equationCombination in combinations(self._equations, number_ofEquations):
            if (system := System_ofLinearEquations(list(equationCombination))).isSolvable():
                solution = system.solve()
                unknownAddresses = list(solution.keys())
                for unknownAddress in unknownAddresses:
                    setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
                    self._updatedUnknowns.append(unknownAddress)

                # If system is solved, all equations in the combination is solved. Remove them from equations pool.
                for equation in equationCombination:
                    self._equations.remove(equation)

    def _add_flowReferences_toStates(self):
        """Adds a 'flow' attribute to all the state objects in all flows included in the cycle. """
        # Not a big fan of doing this - states are a lower level entity than flows and should not have access to the higher level entity which contains it.
        # Instead, they should be accessed from the flows which contain them. But had to resort to this for convenience.
        for flow in self.flows:
            for state in flow.states:
                setattr(state, 'flow', flow)

    def _convertStates_toFlowPoints(self):
        """Iterates over all flows and changes states with FlowPoints based on them."""
        for flow in self.flows:
            for state in flow.states:
                # Replace state with flow point - find the position of the state in the items list, change item at index (i.e. state)
                flow.items[flow.items.index(state)] = FlowPoint(baseState=state, flow=flow)

    def _get_intersections(self):
        """Iterates through flows' items to find intersections. Specifically, checks for shared endpoints and devices."""

        # TODO - Prevent inclusion of turbines with multiple extractions as intersections!

        endPoints = []
        intersections = set()

        # Identify end connections - DEVICES
        for flow in self.flows:
            for endPoint in [flow.items[0], flow.items[-1]]:
                if isinstance(endPoint, Device):  # endPoint may be a state or a device! - pick devices
                    if endPoint not in endPoints:
                        endPoints.append(endPoint)
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

        if isinstance(device, MixingChamber):
            self.solve_mixingChamber(device)

        elif isinstance(device, HeatExchanger):
            self.solve_heatExchanger(device)

        elif isinstance(device, Turbine):
            self._add_turbineMassBalance(device)

    def solve_heatExchanger(self, device: HeatExchanger):
        """Does a heat balance over the flows entering and exiting the heat exchanger, calculates the missing property and sets its value in the relevant object."""
        # m1h11 + m2h21 + m3h31 = m1h12 + m2h22 + m3h32

        # m1(h1i - h1o) + m2(h2i - h2o) + m3(h3i - h3o) = 0
        # heatBalance = LinearEquation([ [ ( (state_in, 'flow.massFF'), state_in.h - state_out.h) for state_in, state_out in device.lines], 0 ])

        heatBalance_LHS = []
        for state_in, state_out in device.lines:
            heatBalance_LHS.append( ((state_in.flow, 'massFF'), (state_in, 'h')) )
            heatBalance_LHS.append( ((-1), (state_out.flow, 'massFF'), (state_out, 'h')) )
        heatBalance = LinearEquation(LHS=heatBalance_LHS, RHS=0)

        if heatBalance.isSolvable():
            heatBalance.solve_and_set()
        else:
            self._equations.append(heatBalance)
            heatBalance.source = device

    def solve_mixingChamber(self, device: MixingChamber):
        """Sets or verifies common mixing pressure on all end states. Does mass & heat balances on flows."""

        # Infer constant mixing pressure
        sampleState_withPressure = None
        for endState in device.endStates:
            if isNumeric(endState.P):
                sampleState_withPressure = endState
                break
        if sampleState_withPressure is not None:
            for endState in [state for state in device.endStates if state is not sampleState_withPressure]:
                endState.set_or_verify({'P': sampleState_withPressure.P})

        # Construct the equations

        # m1 + m2 + m3 - m4 = 0
        massBalance_LHS = []
        for state_in in device.states_in:
            massBalance_LHS.append( (1, (state_in.flow, 'massFF')) )
        massBalance_LHS.append( (-1, (device.state_out.flow, 'massFF')) )
        massBalance = LinearEquation(LHS=massBalance_LHS, RHS=0)

        # m1h1 + m2h2 + m3h3 - m4h4 = 0
        heatBalance_LHS = []
        for state_in in device.states_in:
            heatBalance_LHS.append( ((state_in.flow, 'massFF'), (state_in, 'h')) )
        heatBalance_LHS.append( (-1, (device.state_out.flow, 'massFF'), (device.state_out, 'h')) )
        heatBalance = LinearEquation(LHS=heatBalance_LHS, RHS=0)

        for equation in [massBalance, heatBalance]:
            if equation.isSolvable():
                equation.solve_and_set()
            else:
                self._equations.append(equation)
                equation.source = device

    def _add_turbineMassBalance(self, device: Turbine):
        """Creates a mass balance equation for flows entering/exiting a turbine."""
        massBalance_LHS = []
        massBalance_LHS.append((1, (device.state_in.flow, 'massFF')))
        for state_out in device.states_out:
            massBalance_LHS.append((-1, (state_out.flow, 'massFF')))
        massBalance = LinearEquation(LHS=massBalance_LHS, RHS=0)

        if massBalance.isSolvable():
            massBalance.solve_and_set()
        else:
            self._equations.append(massBalance)
            massBalance.source = device

    def _add_netPowerBalance(self):
        powerBalance_LHS = [ ((self, 'netPower'),) ]
        mainFlow = self._get_mainFlow()
        for flow in self.flows:
            powerBalance_LHS.append((-1, (flow, 'massFF'), (mainFlow, 'massFR'), flow.net_sWorkExtracted))
        powerBalance = LinearEquation(LHS=powerBalance_LHS, RHS=0)
        powerBalance.source = 'Cycles._add_netPowerBalance'
        self._equations.append(powerBalance)

    def _get_mainFlow(self) -> Flow:
        mainFlow = None
        for flow in self.flows:
            if flow.massFF == 1:
                mainFlow = flow
        assert mainFlow is not None, 'InputError: Main flow with mass fraction 1 is not identified by user.'
        return mainFlow

    def _resolve_massFlows(self):
        mainFlow = self._get_mainFlow()
        for flow in self.flows:
            self._equations.append(LinearEquation(LHS=[ (1, (flow, 'massFR')), (-1, (mainFlow, 'massFR'), (flow, 'massFF')) ], RHS=0))