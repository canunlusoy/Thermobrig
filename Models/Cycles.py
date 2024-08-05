
from typing import List, Dict, Set, Union
from itertools import combinations

from Models.Flows import Flow
from Models.Devices import Device, MixingChamber, HeatExchanger, Turbine, Regenerator, Combustor, GasReheater
from Models.States import StatePure, FlowPoint_Pure, StateIGas, FlowPoint_IGas
from Models.Fluids import Fluid, IdealGas
from Utilities.Numeric import isNumeric
from Utilities.PrgUtilities import LinearEquation, System_ofLinearEquations, setattr_fromAddress, updateEquations, solve_solvableEquations, solve_combination_ofEquations


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

        self.log = []
        self.callbacks = []

    def solve(self):

        # Steps for initialization
        if not self._initialSolutionComplete:
            self._convertStates_toFlowPoints()  # At the cycle level, states become FlowPoints, i.e. states that are aware of the flows they are in.

            self._deviceDict = self.get_deviceDict()
            self._regerator_solutionSetups = {}

            if Regenerator in self._deviceDict:
                for regenerator in self._deviceDict[Regenerator]:
                    self._regerator_solutionSetups[regenerator] = False

            # 2 separate loops - device endStates may be from different flows. First set endState references, then work on each device for each flow they are in.
            for flow in self.flows:
                flow._set_devices_endStateReferences()

                flow.log = self.log
                flow.callbacks = self.callbacks

            for flow in self.flows:
                flow.solve()

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

            # Setting up equations
            self._add_net_sPower_relation()
            self._add_sHeat_relation()
            self._add_netPowerBalance()
            self._add_Q_in_relation()

            if self.type == 'power':
                self._add_efficiency_relation()
            elif self.type == 'refrigeration':
                self._add_COP_relation()

            self._add_massFlowRelations()

            for deviceType in [Combustor, GasReheater]:
                if deviceType in self._deviceDict:
                    for device in self._deviceDict[Combustor]:
                        if isNumeric(device.sHeatSupplied):
                            self._add_sHeatSupplied_relation(device)

            updateEquations(self._equations, self._updatedUnknowns)  # updating all equations in case _solveIntersection() above found any of their unknowns
            self._initialSolutionComplete = True
        # Initialization steps completed.

        # Quick and dirty regenerator solution - need to form heat balance equation only once, check each time if equation formed for device.
        if Regenerator in self._deviceDict:
            for regenerator in self._deviceDict[Regenerator]:
                if self._regerator_solutionSetups[regenerator] == False:
                    solution_setup = self.solve_regenerator(regenerator)
                    self._regerator_solutionSetups[regenerator] = solution_setup


        # Review flow devices again in case some properties of some of their endStates became known above
        for flow in self.flows:
            flow.solve()

        updateEquations(self._equations, self._updatedUnknowns)
        updatedUnknowns = solve_solvableEquations(self._equations)
        self._updatedUnknowns.union(updatedUnknowns)

        updateEquations(self._equations, self._updatedUnknowns)
        updatedUnknowns = solve_combination_ofEquations(self._equations, number_ofEquations=2)
        self._updatedUnknowns.union(updatedUnknowns)

        updateEquations(self._equations, self._updatedUnknowns)
        updatedUnknowns = solve_combination_ofEquations(self._equations, number_ofEquations=3)
        self._updatedUnknowns.union(updatedUnknowns)

        updateEquations(self._equations, self._updatedUnknowns)


    def _convertStates_toFlowPoints(self):
        """Iterates over all flows and changes states with FlowPoints based on them."""

        flowPointClasses = {Fluid: FlowPoint_Pure, IdealGas: FlowPoint_IGas}

        for flow in self.flows:
            flowPointClass = flowPointClasses[flow.workingFluid.__class__]  # To create the appropriate FlowPoint based on type of fluid

            for state in flow.states:
                # Replace state with flow point - find the position of the state in the items list, change item at index (i.e. state)
                flow.items[flow.items.index(state)] = flowPointClass(baseState=state, flow=flow, log=self.log)

    def get_deviceDict(self) -> Dict:
        deviceDict = {}
        for flow in self.flows:
            for device in flow.devices:
                if (deviceType:= type(device)) not in deviceDict:
                    deviceDict[deviceType] = {device}
                else:
                    deviceDict[deviceType].add(device)
        return deviceDict

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
        heatBalance = LinearEquation(LHS=heatBalance_LHS, RHS=0, source=device)
        self.solve_or_add_toEquations(heatBalance)

    def solve_regenerator(self, device: Regenerator):

        if all(isNumeric(line[0].T) for line in device.lines):  # Need inlet temperatures of both lines to determine in which direction heat will flow

            warmLine, coldLine = device.lines
            if device.lines[1][0].T > device.lines[0][0].T:   # state_in of device.lines[1]
                coldLine, warmLine = device.lines
            warm_in, warm_out = warmLine
            cold_in, cold_out = coldLine

            assert warm_in.flow.constant_c == cold_in.flow.constant_c, 'solve_regenerator: Flows of the warm and cold lines have different constant_c settings! Not allowed.'
            constant_c = warm_in.flow.constant_c

            if device.counterFlow_commonColdTemperature:
                warm_out.set_or_verify({'T': cold_in.T})

            heatBalance_LHS = []
            # warm_mFF*(warm_in.h - warm_out.h)*effectiveness = cold_mFF*(cold_out.h - cold_in.h)
            # warm_mFF*(warm_in.h - warm_out.h)*effectiveness + cold_mFF*(cold_in.h - cold_out.h) = 0

            if constant_c:
                assert isNumeric(warm_in.flow.workingFluid.cp)
                heatBalance_LHS.append( ((device.effectiveness), (warm_in.flow, 'massFF'), (warm_in.flow.workingFluid.cp), (warm_in, 'T')) )
                heatBalance_LHS.append( ((device.effectiveness), (-1), (warm_out.flow, 'massFF'), (warm_out.flow.workingFluid.cp), (warm_out, 'T')) )

                heatBalance_LHS.append( ((cold_in.flow, 'massFF'), (cold_in.flow.workingFluid.cp), (cold_in, 'T')) )
                heatBalance_LHS.append( ((-1), (cold_out.flow, 'massFF'), (cold_out.flow.workingFluid.cp), (cold_out, 'T')) )

            else:
                heatBalance_LHS.append( ((device.effectiveness), (warm_in.flow, 'massFF'), (warm_in, 'h')) )
                heatBalance_LHS.append( ((device.effectiveness), (-1), (warm_out.flow, 'massFF'), (warm_out, 'h')) )

                heatBalance_LHS.append( ((cold_in.flow, 'massFF'), (cold_in, 'h')) )
                heatBalance_LHS.append( ((-1), (cold_out.flow, 'massFF'), (cold_out, 'h')) )

            heatBalance = LinearEquation(LHS=heatBalance_LHS, RHS=0, source=device)
            self.solve_or_add_toEquations(heatBalance)
            return True  # Regenerator solution setup complete - equation either solved or prepared. No need to visit this method again.

        else:
            return False  # Regenerator solution could not be set up.


    def solve_mixingChamber(self, device: MixingChamber):
        """Sets or verifies common mixing pressure on all end states. Does mass & heat balances on flows."""

        # Infer constant mixing pressure
        device.infer_common_mixingPressure()

        # Construct the equations

        # m1 + m2 + m3 - m4 = 0
        massBalance_LHS = []
        for state_in in device.states_in:
            massBalance_LHS.append( (1, (state_in.flow, 'massFF')) )
        massBalance_LHS.append( (-1, (device.state_out.flow, 'massFF')) )
        massBalance = LinearEquation(LHS=massBalance_LHS, RHS=0, source=device)

        # m1h1 + m2h2 + m3h3 - m4h4 = 0
        heatBalance_LHS = []
        for state_in in device.states_in:
            heatBalance_LHS.append( ((state_in.flow, 'massFF'), (state_in, 'h')) )
        heatBalance_LHS.append( (-1, (device.state_out.flow, 'massFF'), (device.state_out, 'h')) )
        heatBalance = LinearEquation(LHS=heatBalance_LHS, RHS=0, source=device)

        for equation in [massBalance, heatBalance]:
            self.solve_or_add_toEquations(equation)

    def _add_sHeatSupplied_relation(self, device: Union[Combustor, GasReheater]):  # For combustors
        # sHeatSupplied = state_out.h - state_in.h
        # sHeatSupplied + state_in.h - state_out.h = 0
        sHeatSupplied_relation_LHS = [(1, (device, 'sHeatSupplied'))]
        if not device.state_in.flow.constant_c:
            sHeatSupplied_relation_LHS += [ (1, (device.state_in, 'h')), (-1, (device.state_out, 'h')) ]
        else:
            sHeatSupplied_relation_LHS += [ (1, (device.state_in.flow.workingFluid.cp), (device.state_in, 'T')), (-1, (device.state_out.flow.workingFluid.cp), (device.state_out, 'T')) ]

        net_sHeatSupplied_relation = LinearEquation(LHS=sHeatSupplied_relation_LHS, RHS=0, source='Cycles._add_sHeatSupplied_relation')
        self._equations.append(net_sHeatSupplied_relation)

    def _add_turbineMassBalance(self, device: Turbine):
        """Creates a mass balance equation for flows entering/exiting a turbine."""
        massBalance_LHS = []
        massBalance_LHS.append((1, (device.state_in.flow, 'massFF')))
        for state_out in device.states_out:
            massBalance_LHS.append((-1, (state_out.flow, 'massFF')))
        massBalance = LinearEquation(LHS=massBalance_LHS, RHS=0, source=device)
        self.solve_or_add_toEquations(massBalance)

    def _add_netPowerBalance(self):
        """Constructs the power balance equation, i.e. netPower = sum(flow.massFR * workDevice.net_sWorkExtracted for workDevice in flow) for flow in self.flows.
        If netPower is known, this equation can help finding other unknowns such as mass flow rates or state enthalpies. Otherwise, netPower can be obtained vice versa.
        Adds the equation the _equations pool."""
        powerBalance_LHS = [ ((self, 'netPower'),) ]
        mainFlow = self._get_mainFlow()
        for flow in self.flows:
            powerBalance_LHS.append( (-1, (flow, 'massFF'), (mainFlow, 'massFR'), flow.net_sWorkExtracted) )
        powerBalance = LinearEquation(LHS=powerBalance_LHS, RHS=0, source='Cycles._add_netPowerBalance')
        self._equations.append(powerBalance)

    def _add_Q_in_relation(self):
        """Constructs the equation of total heat inputs. If Q_in is a given, can help find other unknowns such as mass flow rates or state
        enthalpies; otherwise, can help determine Q_in."""
        Q_in_relation_LHS = [ ((self, 'Q_in'),) ]
        mainFlow = self._get_mainFlow()
        for flow in self.flows:
            Q_in_relation_LHS.append( (-1, (flow, 'massFF'), (mainFlow, 'massFR'), flow.sHeatSupplied) )
        Q_in_relation = LinearEquation(LHS=Q_in_relation_LHS, RHS=0, source='Cycles._add_Q_in_relation')
        self._equations.append(Q_in_relation)

    def _add_net_sPower_relation(self):
        """Constructs the equation of net work per unit flow, i.e. per kg/s of flow on the mainline."""
        net_sPower_relation_LHS = [ (-1, (self, 'net_sPower'),) ]
        for flow in self.flows:
            net_sPower_relation_LHS.append( ((flow, 'massFF'), flow.net_sWorkExtracted) )
        net_sPower_relation = LinearEquation(LHS=net_sPower_relation_LHS, RHS=0, source='Cycles._add_net_sPower_relation')
        self._equations.append(net_sPower_relation)
        self._net_sPower_relation = net_sPower_relation

    def _add_sHeat_relation(self):
        """Constructs the equation of specific heat input per unit flow (per kg/s) on the mainline."""
        sHeat_relation_LHS = [ (-1, (self, 'sHeat'),) ]
        for flow in self.flows:
            sHeat_relation_LHS.append( ((flow, 'massFF'), flow.sHeatSupplied) )
        net_sPower_relation = LinearEquation(LHS=sHeat_relation_LHS, RHS=0, source='Cycles._add_sHeat_relation')
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
        COP_relation_LHS = [ ( (self, 'COP'), (self._net_sPower_relation.isolate([(self, 'net_sPower'),])) ), (-1, -1, (self._sHeat_relation.isolate([(self, 'sHeat'),]))) ]
        COP_relation = LinearEquation(LHS=COP_relation_LHS, RHS=0)
        self._equations.append(COP_relation)

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

    def get_allDevices(self):
        devices = []
        for flow in self.flows:
            devices += flow.devices
        return set(devices)

    def solve_or_add_toEquations(self, equation: LinearEquation):
        """Solves the equation if solvable, and sets the unknown's value. If not solvable, adds equation to the equations pool."""
        if equation.isSolvable():  # if solvable by itself, there is only one unknown
            solution = equation.solve()
            unknownAddress = list(solution.keys())[0]
            setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
            self._updatedUnknowns.add(unknownAddress)
        else:
            self._equations.append(equation)
