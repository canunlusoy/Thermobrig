import unittest

from typing import Dict, Union

from Models.Cycles import Cycle
from Models.Flows import Flow, IdealGasFlow
from Models.States import StatePure, StateIGas
from Models.Devices import Device, Turbine, Boiler, Condenser, Pump, ClosedFWHeater, OpenFWHeater, Trap, HeatExchanger
from Models.Fluids import Fluid, IdealGas
from Methods.ThprOps import fullyDefine_StatePure, define_StateIGas

from Utilities.FileOps import read_Excel_DF, process_MaterialPropertyDF
from Utilities.Numeric import isWithin

dataFile_path = r'Cengel_Formatted_Unified.xlsx'
dataFile_worksheet = 'WaterUnified'
dataFile = read_Excel_DF(dataFile_path, worksheet=dataFile_worksheet, headerRow=1, skipRows=[0])
water_mpDF = process_MaterialPropertyDF(dataFile)

dataFile = read_Excel_DF(dataFile_path, worksheet='R134aUnified', headerRow=1, skipRows=[0])
R134a_mpDF = process_MaterialPropertyDF(dataFile)

dataFile = read_Excel_DF(dataFile_path, worksheet='Air', headerRow=1, skipRows=[0])
air_mpDF = process_MaterialPropertyDF(dataFile)

air = IdealGas(air_mpDF, R=0.2870)
water = Fluid(water_mpDF)
R134a = Fluid(R134a_mpDF)

class TestFlows(unittest.TestCase):

    def CompareResults(self, testState: StatePure, expected: Dict, ptolerance: Union[float, int]):
        print('\n')
        for parameter in expected:
            assert hasattr(testState, parameter)
            self.assertTrue(isWithin(getattr(testState, parameter), ptolerance, '%', expected[parameter]))
            print('Expected: {0}'.format(expected[parameter]))
            print('Received: {0}'.format(getattr(testState, parameter)))

    def test_flows_water_01(self):
        # From MECH2201 - A9 Q1
        # Net power = 80 MW
        # x after Turbine, mass flow rate, thermal efficiency?

        flow = Flow(workingFluid=water)
        flow.items = [state_0 := StatePure(P=10000, T=500),  # State 0
                      Turbine(eta_isentropic=0.8),
                      StatePure(P=1000),  # State 1
                      rhboiler := Boiler(),
                      StatePure(T=500),  # State 2
                      Turbine(eta_isentropic=0.8),
                      StatePure(),  # State 3
                      Condenser(),
                      StatePure(P=10, x=0),  # State 4
                      Pump(eta_isentropic=0.95),
                      StatePure(),  # State 5
                      rhboiler,
                      state_0]

        # Solution process:
        # State 0 - fully definable
        # State 1 - work out with isentropic efficiency
        # State 2 - infer pressure from State 1, fully definable
        # State 3 - infer pressure from 4, work out with isentropic efficiency
        # State 4 - fully definable

        flow.solve()

        self.CompareResults(flow.states[0], {'h': 3373.7, 's': 6.5966}, 3)
        self.CompareResults(flow.states[1], {'h': 2920.6}, 3)
        self.CompareResults(flow.states[2], {'h': 3478.5, 's': 7.7622}, 3)
        self.CompareResults(flow.states[3], {'T': 87.8, 'h': 2664.4}, 3)
        self.CompareResults(flow.states[4], {'h': 191.83, 's': 0.6493}, 3)
        self.CompareResults(flow.states[5], {'h': 202.45}, 3)

        netPower = 80000
        massFlowRate = netPower / flow.net_sWorkExtracted
        eta_thermal = flow.net_sWorkExtracted / flow.sHeatSupplied
        x_afterTurbine = flow.states[3].x

        self.assertTrue(isWithin(massFlowRate, 3, '%', 63.66))
        print('Expected: ', 63.66)
        print('Received: ', massFlowRate)
        self.assertTrue(isWithin(eta_thermal, 3, '%', 0.34))
        print('Expected: ', 0.34)
        print('Received: ', eta_thermal)
        self.assertTrue(isWithin(x_afterTurbine, 3, '%', 2))
        print('Expected: ', 2)
        print('Received: ', x_afterTurbine)

    def test_flows_water_02(self):

        # MECH 2201 - A9 Q2

        flow_a = Flow(water)
        flow_a.massFR = 42
        flow_a.massFF = 1
        flow_a.items = [ofwh := OpenFWHeater(),
                        state_7 := StatePure(x=0),
                        Pump(),
                        state_8 := StatePure(P=15000),
                        heatExchanger := HeatExchanger(),
                        state_9 := StatePure(T=water.define(StatePure(P=600, x=0)).T),
                        boiler := Boiler(infer_fixed_exitT=False),
                        state_1 := StatePure(P=15000, T=600),
                        turbine_a := Turbine(),
                        state_2 := StatePure(P=1000),
                        boiler,
                        state_3 := StatePure(P=1000, T=500),
                        turbine_b := Turbine(),
                        state_10 := StatePure(P=600)]

        flow_b = Flow(water)
        flow_b.items = [state_10,
                        heatExchanger,
                        state_11 := StatePure(x=0),
                        Trap(),
                        state_12 := StatePure(P=200),
                        ofwh]

        flow_c = Flow(water)
        flow_c.items = [state_10,
                        turbine_b,
                        state_13 := StatePure(P=200),
                        ofwh]

        flow_d = Flow(water)
        flow_d.items = [state_10,
                        turbine_b,
                        state_13,
                        turbine_b,
                        state_4 := StatePure(),
                        condenser := Condenser(),
                        state_5 := StatePure(P=5, x=0),
                        Pump(),
                        state_6 := StatePure(P=200),
                        ofwh]

        cycle = Cycle()
        cycle.flows = [flow_a,
                       flow_b,
                       flow_c,
                       flow_d]

        for flow in cycle.flows:
            flow._calculate_h_forIncompressibles = True

        cycle.solve()



        print(3)

    def test_flows_water_03(self):

        print('CENGEL P10.57')

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.items = [condenser := Condenser(),
                        state_1 := StatePure(P=20),
                        Pump(),
                        state_2 := StatePure(P=5000),
                        cfwhA_transit := (cfwhA := ClosedFWHeater()).add_newBundle(),
                        state_3 := StatePure(),
                        cfwhB_main := (cfwhB := ClosedFWHeater()).add_newBundle(),
                        state_4 := StatePure(),
                        Boiler(),
                        state_5 := StatePure(T=700),
                        turbine := Turbine(eta_isentropic=1)]

        flow_b = Flow(water)
        flow_b.massFF = 0.1446
        flow_b.items = [turbine,
                        state_6 := StatePure(P=1400),
                        cfwhB_second := cfwhB.add_newBundle(),
                        state_9 := StatePure(),
                        Trap(),
                        state_10 := StatePure(),
                        cfwhA_mixing := cfwhA.add_newBundle()]

        flow_c = Flow(water)
        flow_c.items = [turbine,
                        state_7 := StatePure(P=245),
                        cfwhA_mixing]

        flow_d = Flow(water)
        flow_d.items = [cfwhA_mixing,
                        state_11 := StatePure(),
                        Trap(),
                        state_12 := StatePure(),
                        condenser]

        flow_e = Flow(water)
        flow_e.items = [turbine,
                        state_8 := StatePure(P=20),
                        condenser]

        cycle = Cycle()
        cycle.flows = [flow_a,
                       flow_b,
                       flow_c,
                       flow_d,
                       flow_e]
        cycle.solve()
        print(4)


    # def test_flows_air_01(self):
    #
    #     flow = IdealGasFlow(workingFluid=air)
    #
    #     flow.items = []

