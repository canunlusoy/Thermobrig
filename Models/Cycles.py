
from typing import List, Dict, Set
from itertools import combinations

from Models.Flows import Flow
from Models.Devices import Device, MixingChamber, HeatExchanger, Turbine
from Models.States import StatePure, FlowPoint
from Utilities.Numeric import isNumeric
from Utilities.PrgUtilities import LinearEquation, System_ofLinearEquations, setattr_fromAddress


class Cycle:

    def __init__(self, type: str = 'power'):
        self.type = type

        self.flows: List[Flow] = []

        # Overall values
        self.netPower = float('nan')
        self.Q_in = float('nan')

        # Specific values (per kg/s of flow on the mainline)
        self.net_sPower = float('nan')
        self.sHeat = float('nan')

        if self.type == 'power':
            self.efficiency = float('nan')
        elif self.type == 'refrigeration':
            self.COP = float('nan')

        self._equations: List[LinearEquation] = []
        self._initialSolutionComplete = False
        self._solvedEquations = []
        self._updatedUnknowns = set()

        self.intersections = None

    def updateEquations(self, updateAll: bool = False):
        for equation in self._equations:
            if updateAll or any(unknown in equation.get_unknowns() for unknown in self._updatedUnknowns):
                equation.update()
            self._updatedUnknowns = set()

    def solve(self):

        # Steps for initialization
        if not self._initialSolutionComplete:
            self._convertStates_toFlowPoints()

            # 2 separate loops - device endStates may be from different flows. First set endState references, then work on each device for each flow they are in.
            for flow in self.flows:
                flow._set_devices_endStateReferences()

            for flow in self.flows:
                flow.solve()

            # Get updated unknowns (i.e. defined states) from flow solution

            # TODO #######################################################################

            # Identify areas where flows interact, e.g. heat exchangers or flow connections
            self.intersections = self._get_intersections()

            if not all(flow.isFullyDefined() for flow in self.flows):
                for device in self.intersections:
                    self._solveIntersection(device)  # constructs equations for intersections & adds to the pool

            # Review intersections, construct equations & attempt to solve - if there are undefined states around them
            # This process needs to be done only once since equations need to be constructed once. Then they are added to the _equations pool.
            # intersections_attempted_toSolve = []  # list of intersection devices on which the _solveIntersection() has been run - keeping track not to run the _solveIntersection twice on the same device
            # for state in self.get_undefinedStates():
            #     surroundingDevices = state.flow.get_surroundingItems(state)
            #     for surroundingDevice in surroundingDevices:
            #         if surroundingDevice in self.intersections and surroundingDevice not in intersections_attempted_toSolve:
            #             self._solveIntersection(surroundingDevice)
            #             intersections_attempted_toSolve.append(surroundingDevice)

            self._add_net_sPower_relation()
            self._add_sHeat_relation()
            self._add_netPowerBalance()
            self._add_Q_in_relation()

            if self.type == 'power':
                self._add_efficiency_relation()
            elif self.type == 'refrigeration':
                self._add_COP_relation()

            self._add_massFlowRelations()

            self.updateEquations()  # updating all equations in case _solveIntersection() above found any of their unknowns
            self._initialSolutionComplete = True
        # Initialization steps completed.


        # Review flow devices again in case some properties of some of their endStates became known above
        for flow in self.flows:
            flow.solve()

        self.updateEquations()
        self._solve_solvableEquations()
        self.updateEquations()
        self._solve_combination_ofEquations(number_ofEquations=2)
        self.updateEquations()
        self._solve_combination_ofEquations(number_ofEquations=3)
        self.updateEquations()


    def _solve_solvableEquations(self):
        solvedEquations = []
        for equation in self._equations:
            equation.update()
            if equation.isSolvable():
                solution = equation.solve()
                unknownAddress = list(solution.keys())[0]
                setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
                self._updatedUnknowns.add(unknownAddress)
                solvedEquations.append(equation)

        for equation in solvedEquations:
            self._equations.remove(equation)

    def _solve_combination_ofEquations(self, number_ofEquations: int):
        """Iterates through combinations of equations (from the _equations pool) with the specified number_ofEquations. For each combination, checks if the
        system is solvable. If so, solves it, assigns the unknowns the solution values and removes the solved equations from the _equations pool."""
        for equationCombination in combinations(self._equations, number_ofEquations):

            # If any of the equations got solved in a previous iteration and got removed from _equations, skip this combination
            # Combinations are generated beforehand at the beginning of the main for loop.
            if any(equation not in self._equations for equation in equationCombination):
                continue

            if (system := System_ofLinearEquations(list(equationCombination))).isSolvable():
                solution = system.solve()
                unknownAddresses = list(solution.keys())
                for unknownAddress in unknownAddresses:
                    setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
                    self._updatedUnknowns.add(unknownAddress)

                # If system is solved, all equations in the combination is solved. Remove them from equations pool.
                for equation in equationCombination:
                    self._equations.remove(equation)

    def _convertStates_toFlowPoints(self):
        """Iterates over all flows and changes states with FlowPoints based on them."""
        for flow in self.flows:
            for state in flow.states:
                # Replace state with flow point - find the position of the state in the items list, change item at index (i.e. state)
                flow.items[flow.items.index(state)] = FlowPoint(baseState=state, flow=flow)

    def _get_intersections(self):
        """Iterates through flows' items to find intersections. Specifically, checks for shared endpoints and devices."""
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
        """Constructs the heat balance equation over the flows entering and exiting the heat exchanger. If equation is solvable as is (i.e. has 1 unknown), calculates the missing property
        and sets its value in the relevant object."""

        # m1h11 + m2h21 + m3h31 = m1h12 + m2h22 + m3h32
        # m1(h1i - h1o) + m2(h2i - h2o) + m3(h3i - h3o) = 0
        # heatBalance = LinearEquation([ [ ( (state_in, 'flow.massFF'), state_in.h - state_out.h) for state_in, state_out in device.lines], 0 ])

        heatBalance_LHS = []
        for state_in, state_out in device.lines:
            heatBalance_LHS.append( ((state_in.flow, 'massFF'), (state_in, 'h')) )
            heatBalance_LHS.append( ((-1), (state_out.flow, 'massFF'), (state_out, 'h')) )
        heatBalance = LinearEquation(LHS=heatBalance_LHS, RHS=0)

        if heatBalance.isSolvable():  # if solvable by itself, there is only one unknown
            solution = heatBalance.solve()
            unknownAddress = list(solution.keys())[0]
            setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
            self._updatedUnknowns.add(unknownAddress)
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
                solution = equation.solve()
                unknownAddress = list(solution.keys())[0]
                setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
                self._updatedUnknowns.add(unknownAddress)
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
        massBalance.source = device

        if massBalance.isSolvable():
            solution = massBalance.solve()
            unknownAddress = list(solution.keys())[0]
            setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
            self._updatedUnknowns.add(unknownAddress)
        else:
            self._equations.append(massBalance)

    def _add_netPowerBalance(self):
        """Constructs the power balance equation, i.e. netPower = sum(flow.massFR * workDevice.net_sWorkExtracted for workDevice in flow) for flow in self.flows.
        If netPower is known, this equation can help finding other unknowns such as mass flow rates or state enthalpies. Otherwise, netPower can be obtained vice versa.
        Adds the equation the _equations pool."""
        powerBalance_LHS = [ ((self, 'netPower'),) ]
        mainFlow = self._get_mainFlow()
        for flow in self.flows:
            powerBalance_LHS.append( (-1, (flow, 'massFF'), (mainFlow, 'massFR'), flow.net_sWorkExtracted) )
        powerBalance = LinearEquation(LHS=powerBalance_LHS, RHS=0)
        powerBalance.source = 'Cycles._add_netPowerBalance'
        self._equations.append(powerBalance)

    def _add_Q_in_relation(self):
        """Constructs the equation of total heat inputs. If Q_in is a given, can help find other unknowns such as mass flow rates or state
        enthalpies; otherwise, can help determine Q_in."""
        Q_in_relation_LHS = [ ((self, 'Q_in'),) ]
        mainFlow = self._get_mainFlow()
        for flow in self.flows:
            Q_in_relation_LHS.append( (-1, (flow, 'massFF'), (mainFlow, 'massFR'), flow.sHeatSupplied) )
        Q_in_relation = LinearEquation(LHS=Q_in_relation_LHS, RHS=0)
        Q_in_relation.source = 'Cycles._add_Q_in_relation'
        self._equations.append(Q_in_relation)

    def _add_net_sPower_relation(self):
        """Constructs the equation of net work per unit flow, i.e. per kg/s of flow on the mainline."""
        net_sPower_relation_LHS = [ (-1, (self, 'net_sPower'),) ]
        for flow in self.flows:
            net_sPower_relation_LHS.append( ((flow, 'massFF'), flow.net_sWorkExtracted) )
        net_sPower_relation = LinearEquation(LHS=net_sPower_relation_LHS, RHS=0)
        net_sPower_relation.source = 'Cycles._add_net_sPower_relation'
        self._equations.append(net_sPower_relation)
        self._net_sPower_relation = net_sPower_relation

    def _add_sHeat_relation(self):
        """Constructs the equation of specific heat input per unit flow (per kg/s) on the mainline."""
        sHeat_relation_LHS = [ (-1, (self, 'sHeat'),) ]
        for flow in self.flows:
            sHeat_relation_LHS.append( ((flow, 'massFF'), flow.sHeatSupplied) )
        net_sPower_relation = LinearEquation(LHS=sHeat_relation_LHS, RHS=0)
        net_sPower_relation.source = 'Cycles._add_sHeat_relation'
        self._equations.append(net_sPower_relation)
        self._sHeat_relation = net_sPower_relation

    def _add_efficiency_relation(self):
        """Constructs the equation of thermal efficiency of the complete cycle."""
        # eta = wnet_o / q_in -> eta * q_in = wnet_o
        eta_relation_LHS = [ ( (self, 'efficiency'), (self._sHeat_relation.isolate([(self, 'sHeat'),])) ), (-1, (self._net_sPower_relation.isolate([(self, 'net_sPower'),]))) ]
        eta_relation = LinearEquation(LHS=eta_relation_LHS, RHS=0)
        self._equations.append(eta_relation)

    def _add_COP_relation(self):
        """Constructs the equation of the coefficient of performance (COP) of the complete cycle."""
        # COP = Q_in/W_in
        # TODO: COP_relation_LHS = [ ( (self, 'COP'), (self.) ) ]

    def _get_mainFlow(self) -> Flow:
        """Returns the flow whose mass flow fraction is 1."""
        mainFlow = None
        for flow in self.flows:
            if flow.massFF == 1:
                mainFlow = flow
        assert mainFlow is not None, 'InputError: Main flow with mass fraction 1 is not identified by user.'
        return mainFlow

    def _add_massFlowRelations(self):
        """Expects main flow (flow with mass flow fraction = 1) to be identified already. Constructs the equation **mainFlow.massFR * flow.massFF = flow.massFR** for each flow. Adds the equation for each flow
        to the _equations pool."""
        mainFlow = self._get_mainFlow()
        for flow in self.flows:
            self._equations.append(LinearEquation(LHS=[ (1, (flow, 'massFR')), (-1, (mainFlow, 'massFR'), (flow, 'massFF')) ], RHS=0))

    def get_undefinedStates(self) -> List[StatePure]:
        """Returns a list of all (non-repeating) undefined states included in the cycle, i.e. considers states from all flows in the cycle."""
        toReturn = []
        for flow in self.flows:
            for state in flow.get_undefinedStates():
                if state not in toReturn:
                    toReturn.append(state)
        return toReturn
