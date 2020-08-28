import unittest

from typing import Dict, Union

from Models.Cycles import Cycle
from Models.Flows import Flow, IdealGasFlow
from Models.States import StatePure, StateIGas
from Models.Devices import Device, Turbine, Boiler, Condenser, Pump, ClosedFWHeater, MixingChamber, OpenFWHeater, Trap, HeatExchanger, ReheatBoiler
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
            print('Expected: {0}'.format(expected[parameter]))
            print('Received: {0}'.format(getattr(testState, parameter)))
            self.assertTrue(isWithin(getattr(testState, parameter), ptolerance, '%', expected[parameter]))

    def test_flows_water_01(self):
        # From MECH2201 - A9 Q1
        # Net power = 80 MW
        # x after Turbine, mass flow rate, thermal efficiency?

        flow = Flow(workingFluid=water)
        flow.items = [state_0 := StatePure(P=10000, T=500),  # State 0
                      turba := Turbine(eta_isentropic=0.8),
                      state_1 := StatePure(P=1000),  # State 1
                      rhboiler := ReheatBoiler(),
                      state_2 := StatePure(T=500),  # State 2
                      turbb := Turbine(eta_isentropic=0.8),
                      state_3 := StatePure(),  # State 3
                      cond := Condenser(),
                      state_4 := StatePure(P=10, x=0),  # State 4
                      pump := Pump(eta_isentropic=0.95),
                      state_5 := StatePure(),  # State 5
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
        massFlowRate = netPower / flow.get_net_sWorkExtracted()
        eta_thermal = flow.get_net_sWorkExtracted() / flow.sHeatSupplied
        x_afterTurbine = flow.states[3].x

        print('Expected: ', 63.66)
        print('Received: ', massFlowRate)
        self.assertTrue(isWithin(massFlowRate, 3, '%', 63.66))

        print('Expected: ', 0.34)
        print('Received: ', eta_thermal)
        self.assertTrue(isWithin(eta_thermal, 5, '%', 0.34))

        print('Expected: ', 2)
        print('Received: ', x_afterTurbine)
        self.assertTrue(isWithin(x_afterTurbine, 3, '%', 2))


    def test_flows_water_02(self):

        # MECH 2201 - A9 Q2

        flow_a = Flow(water)
        flow_a.massFR = 42
        flow_a.massFF = 1
        flow_a.items = [ofwh := OpenFWHeater(),
                        state_03 := StatePure(x=0),
                        Pump(),
                        state_04 := StatePure(P=15000),
                        heatExchanger := HeatExchanger(),
                        state_05 := StatePure(T=water.define(StatePure(P=600, x=0)).T),
                        rhboiler := ReheatBoiler(),
                        state_08 := StatePure(P=15000, T=600),
                        hpt := Turbine(),
                        state_09 := StatePure(P=1000),
                        rhboiler,
                        state_10 := StatePure(P=1000, T=500),
                        lpt := Turbine()]

        flow_b = Flow(water)
        flow_b.items = [lpt,
                        state_11 := StatePure(P=600),
                        heatExchanger,
                        state_06 := StatePure(x=0),
                        Trap(),
                        state_07 := StatePure(P=200),
                        ofwh]

        flow_c = Flow(water)
        flow_c.items = [lpt,
                        state_12 := StatePure(P=200),
                        ofwh]

        flow_d = Flow(water)
        flow_d.items = [lpt,
                        state_13 := StatePure(),
                        condenser := Condenser(),
                        state_01 := StatePure(P=5, x=0),
                        Pump(),
                        state_02 := StatePure(P=200),
                        ofwh]

        cycle = Cycle()
        cycle.flows = [flow_a,
                       flow_b,
                       flow_c,
                       flow_d]

        for flow in cycle.flows:
            flow._calculate_h_forIncompressibles = True

        cycle.solve()

        self.CompareResults(state_01, {'h': 137.75, 'mu': 0.001005}, 3)
        self.CompareResults(state_02, {'h': 137.95}, 3)
        self.CompareResults(state_03, {'h': 504.71, 'mu': 0.001061}, 3)
        self.CompareResults(state_04, {'h': 520.41}, 3)
        self.CompareResults(state_06, {'h': 670.38, 'mu': 0.001101}, 3)
        self.CompareResults(state_05, {'h': 686.23}, 3)
        self.CompareResults(state_08, {'h': 3583.1, 's': 6.6796}, 3)
        self.CompareResults(state_09, {'h': 2820.8}, 3)
        self.CompareResults(state_10, {'h': 3479.1, 's': 7.7642}, 3)
        self.CompareResults(state_11, {'h': 3310.2}, 3)
        self.CompareResults(state_12, {'h': 3000.9}, 3)
        self.CompareResults(state_13, {'x': 0.9205, 'h': 2368.1}, 3)

        self.assertTrue(isWithin(flow_b.massFF, 5, '%', 0.06287))
        self.assertTrue(isWithin(flow_c.massFF, 3, '%', 0.1165))
        self.assertTrue(isWithin(cycle.netPower, 3, '%', 77447))




    def test_flows_water_03(self):

        print('CENGEL P10.57')

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.massFR = 75
        flow_a.items = [condenser := Condenser(),
                        state_01 := StatePure(P=20),
                        pump := Pump(),
                        state_02 := StatePure(P=5000),
                        cfwha := HeatExchanger(),
                        state_03 := StatePure(),
                        cfwhb := HeatExchanger(),
                        state_04 := StatePure(),
                        boiler := Boiler(),
                        state_05 := StatePure(T=700),
                        turbine := Turbine()]

        flow_b = Flow(water)
        flow_b.massFF = 0.1446
        flow_b.items = [turbine,
                        state_06 := StatePure(P=1400),
                        cfwhb,
                        state_09 := StatePure(),
                        trapb := Trap(),
                        state_10 := StatePure(),
                        mixc := MixingChamber()]

        flow_c = Flow(water)
        flow_c.items = [turbine,
                        state_07 := StatePure(P=245),
                        mixc]

        flow_f = Flow(water)
        flow_f.items = [mixcCond := MixingChamber(),
                        state_im := StatePure(),
                        condenser]

        flow_d = Flow(water)
        flow_d.items = [mixc,
                        state_11 := StatePure(),
                        trapa := Trap(),
                        state_12 := StatePure(),
                        mixcCond]

        flow_e = Flow(water)
        flow_e.items = [turbine,
                        state_08 := StatePure(P=20),
                        mixcCond]

        c = Cycle()
        c.flows = [flow_a, flow_b, flow_c, flow_d, flow_e, flow_f]
        c.solve()
        print(5)


    def test_flows_water_04(self):

        # MECH 2201 - A9 Q3

        water = Fluid(mpDF=water_mpDF)

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.items = [mixCh := MixingChamber(),
                        state_12 := StatePure(),
                        boiler := Boiler(),
                        state_01 := StatePure(P=12000, T=520),
                        turbine := Turbine(eta_isentropic=1)]

        flow_b = Flow(water)
        flow_b.items = [turbine,
                        state_02 := StatePure(P=1000),
                        cfwh := HeatExchanger(),
                        state_10 := StatePure(x=0),
                        pump1 := Pump(),
                        state_11 := StatePure(P=12000),
                        mixCh]

        flow_c = Flow(water)
        flow_c.items = [turbine,
                        state_03 := StatePure(P=150),
                        ofwh := OpenFWHeater()]

        flow_d = Flow(water)
        flow_d.items = [turbine,
                        state_04 := StatePure(P=6),
                        condenser := Condenser(),
                        state_05 := StatePure(x=0),
                        pump2 := Pump(),
                        state_06 := StatePure(P=150),
                        ofwh]

        flow_e = Flow(water)
        flow_e.items = [ofwh,
                        state_07 := StatePure(P=150, x=0),
                        pump3 := Pump(),
                        state_08 := StatePure(P=12000),
                        cfwh,
                        state_09 := StatePure(T=170),
                        mixCh]

        cycle = Cycle()
        cycle.flows = [flow_a, flow_b, flow_c, flow_d, flow_e]
        cycle.netPower = 320000
        cycle.solve()

        for e in cycle._equations:
            e.update()

        cycle.solve()

        for e in cycle._equations:
            e.update()

        cycle.solve()

        Qtot = 0
        for f in cycle.flows:
            f.get_sHeatSupplied()


    # def test_flows_air_01(self):
    #
    #     flow = IdealGasFlow(workingFluid=air)
    #
    #     flow.items = []

