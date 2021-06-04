import unittest

from typing import Dict, Union

from Models.Cycles import Cycle
from Models.Flows import Flow
from Models.States import StatePure, StateIGas
from Models.Devices import Device, Turbine, Boiler, Condenser, Pump, Compressor, IGasCompressor, Combustor, ClosedFWHeater, \
    MixingChamber, OpenFWHeater, Trap, HeatExchanger, ReheatBoiler, Intercooler, GasReheater, Regenerator, Exhaust
from Models.Fluids import Fluid, IdealGas
from Methods.ThprOps import fullyDefine_StatePure, fullyDefine_StateIGas, apply_IGasLaw

from Utilities.FileOps import read_Excel_DF, process_MaterialPropertyDF
from Utilities.Numeric import isWithin
from Utilities.PrgUtilities import LinearEquation

dataFile_path = r'Cengel_Formatted_Unified.xlsx'
dataFile_worksheet = 'WaterUnified'
dataFile = read_Excel_DF(dataFile_path, worksheet=dataFile_worksheet, headerRow=1, skipRows=[0])
water_mpDF = process_MaterialPropertyDF(dataFile)

dataFile = read_Excel_DF(dataFile_path, worksheet='R134aUnified', headerRow=1, skipRows=[0])
R134a_mpDF = process_MaterialPropertyDF(dataFile)

dataFile = read_Excel_DF(dataFile_path, worksheet='Air', headerRow=1, skipRows=[0])
air_mpDF = process_MaterialPropertyDF(dataFile)

air = IdealGas(air_mpDF, R=0.2870, k=1.4, cp=1.005)
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
        flow.items = [state_3 := StatePure(P=10000, T=500),  # State 0
                      turba := Turbine(eta_isentropic=0.8),
                      state_4 := StatePure(P=1000),  # State 1
                      rhboiler := ReheatBoiler(),
                      state_5 := StatePure(T=500),  # State 2
                      turbb := Turbine(eta_isentropic=0.8),
                      state_6 := StatePure(),  # State 3
                      cond := Condenser(),
                      state_1 := StatePure(P=10, x=0),  # State 4
                      pump := Pump(eta_isentropic=0.95),
                      state_2 := StatePure(),  # State 5
                      rhboiler,
                      state_3]
        flow.massFF = 1

        # Solution process:
        # State 0 - fully definable
        # State 1 - work out with isentropic efficiency
        # State 2 - infer pressure from State 1, fully definable
        # State 3 - infer pressure from 4, work out with isentropic efficiency
        # State 4 - fully definable

        # flow.solve()
        cycle = Cycle()
        cycle.flows = [flow]
        cycle.netPower = 80000
        cycle.solve()

        self.CompareResults(state_3, {'h': 3375.1, 's': 6.5995}, 3)
        self.CompareResults(state_4, {'h': 2902}, 3)
        self.CompareResults(state_5, {'h': 3479.1, 's': 7.7642}, 3)
        self.CompareResults(state_6, {'T': 88.1, 'h': 2664.8}, 3)
        self.CompareResults(state_1, {'h': 191.81, 'mu': 0.001010, 's': 0.6493}, 3)
        self.CompareResults(state_2, {'h': 202.43}, 3)

        eta_thermal = cycle.netPower / cycle.Q_in
        x_afterTurbine = flow.states[3].x

        print('Expected: ', 63.66)
        print('Received: ', flow.massFR)
        self.assertTrue(isWithin(flow.massFR, 3, '%', 63.66))

        print('Expected: ', 0.34)
        print('Received: ', eta_thermal)
        self.assertTrue(isWithin(eta_thermal, 5, '%', 0.34))

        print('Expected: ', 2)
        print('Received: ', x_afterTurbine)
        self.assertTrue(isWithin(x_afterTurbine, 3, '%', 2))

        pass

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
                        rhboiler := ReheatBoiler(infer_fixed_exitT=False),
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

        # difference in state_05.h causes difference in flow_b.massFF
        # state_05.h looked up from table in here - in solution, vdP is used

        # for flow in cycle.flows:
        #     flow._calculate_h_forIncompressibles = True

        cycle.solve()
        for e in cycle._equations:
            e.update()
        cycle.solve()

        self.CompareResults(state_01, {'h': 137.75, 'mu': 0.001005}, 3)
        self.CompareResults(state_02, {'h': 137.95}, 3)
        self.CompareResults(state_03, {'h': 504.71, 'mu': 0.001061}, 3)
        self.CompareResults(state_04, {'h': 520.41}, 3)
        self.CompareResults(state_06, {'h': 670.38, 'mu': 0.001101}, 3)
        self.CompareResults(state_05, {'h': 686.23}, 3)  # solution uses h calculated with mu*dP - we use table interpolation - ours should be more accurate?
        self.CompareResults(state_08, {'h': 3583.1, 's': 6.6796}, 3)
        self.CompareResults(state_09, {'h': 2820.8}, 3)
        self.CompareResults(state_10, {'h': 3479.1, 's': 7.7642}, 3)
        self.CompareResults(state_11, {'h': 3310.2}, 3)
        self.CompareResults(state_12, {'h': 3000.9}, 3)
        self.CompareResults(state_13, {'x': 0.9205, 'h': 2368.1}, 3)

        # self.assertTrue(isWithin(flow_b.massFF, 3, '%', 0.06287))  # our state_05.h causes difference in this.
        self.assertTrue(isWithin(flow_c.massFF, 3, '%', 0.1165))
        self.assertTrue(isWithin(cycle.netPower, 3, '%', 72447))
        self.assertTrue(isWithin(cycle.netPower / cycle.Q_in, 3, '%', 0.485))

        pass

    def test_flows_water_03(self):

        print('CENGEL P10.57')

        # h3 = h11 ? says solutions
        # h4 = h9

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.massFR = 75
        flow_a.items = [mixcCond := MixingChamber(),
                        state_i := StatePure(),
                        condenser := Condenser(),
                        state_01 := StatePure(P=20, x=0),
                        pump := Pump(),
                        state_02 := StatePure(P=5000),
                        cfwhA := HeatExchanger(infer_common_exitT=True),
                        state_03 := StatePure(),
                        cfwhB := HeatExchanger(infer_common_exitT=True),
                        state_04 := StatePure(),
                        boiler := Boiler(),
                        state_05 := StatePure(P=5000, T=700),
                        turbine := Turbine()]

        flow_b = Flow(water)
        flow_b.massFF = 0.1446
        flow_b.items = [turbine,
                        state_06 := StatePure(P=1400),
                        cfwhB,
                        state_09 := StatePure(x=0),
                        trap := Trap(),
                        state_10 := StatePure(),
                        mixcI := MixingChamber()]

        flow_c = Flow(water)
        flow_c.items = [turbine,
                        state_07 := StatePure(P=245),
                        mixcI]

        flow_e = Flow(water)
        flow_e.items = [mixcI,
                        state_i2 := StatePure(),
                        cfwhA,
                        state_11 := StatePure(x=0),
                        trapA := Trap(),
                        state_12 := StatePure(),
                        mixcCond]

        flow_d = Flow(water)
        flow_d.items = [turbine,
                        state_08 := StatePure(P=20),
                        mixcCond]

        cycle = Cycle()
        cycle.flows = [flow_a, flow_b, flow_c, flow_d, flow_e]
        cycle.solve()

        # Todo - first 0-1-2 equations are solvable together

        self.CompareResults(state_01, {'h': 251, 'mu': 0.00102}, 3)
        self.CompareResults(state_02, {'h': 256.1}, 3)
        self.CompareResults(state_03, {'h': 533}, 3)
        self.CompareResults(state_11, {'h': state_03.h}, 3)
        self.CompareResults(state_04, {'h': 830}, 3)

        self.assertTrue(isWithin(flow_c.massFF, 3, '%', 0.09810))
        self.assertTrue(isWithin(cycle.netPower, 3, '%', 93000))
        self.assertTrue(isWithin(cycle.netPower / cycle.Q_in, 3, '%', 0.404))

        pass

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

        self.CompareResults(state_01, {'h': 3401.8, 's': 6.5555}, 3)
        self.CompareResults(state_02, {'h': 2764.2, 'x': 0.9931}, 3)
        self.CompareResults(state_03, {'h': 2436.9, 's': state_01.s}, 3)
        self.CompareResults(state_04, {'h': 2018.3, 'x': 0.7727}, 3)
        self.CompareResults(state_05, {'h': 151.53}, 3)
        self.CompareResults(state_06, {'h': 151.67}, 3)
        self.CompareResults(state_07, {'h': 467.11}, 3)
        self.CompareResults(state_08, {'h': 479.59}, 3)
        self.CompareResults(state_09, {'h': 725.86}, 3)
        self.CompareResults(state_10, {'h': 762.81}, 3)
        self.CompareResults(state_11, {'h': 775.21}, 3)

        self.CompareResults(flow_b, {'massFF': 0.1096}, 3)

        self.CompareResults(state_12, {'h': 731.27}, 3)

        self.CompareResults(flow_c, {'massFF': 0.1229}, 3)

        self.assertTrue(isWithin(state_01.h - state_02.h + (1 - flow_b.massFF) * (state_02.h - state_03.h) + (1 - flow_b.massFF - flow_c.massFF) * (state_03.h - state_04.h), 3, '%', 1250.3))

        efficiency = cycle.netPower / cycle.Q_in
        self.assertTrue(isWithin(efficiency, 3, '%', 0.463))
        self.assertTrue(isWithin(3600 * flow_a.massFR, 3, '%', 9.31 * 10**5))

    def test_flows_water_05(self):
        # CENGEL P10-53

        flow_a = Flow(workingFluid=water)
        flow_a.massFF = 1
        flow_a.items = [ofwh := MixingChamber(),
                        state_03 := StatePure(x=0),
                        pump2 := Pump(),
                        state_04 := StatePure(),
                        cfwh := HeatExchanger(),
                        state_05 := StatePure(T=water.define(StatePure(x=0, P=1200)).T),
                        boiler := Boiler(),
                        state_08 := StatePure(P=10000, T=600),
                        turbine := Turbine()]

        flow_b = Flow(water)
        flow_b.items = [turbine,
                        state_09 := StatePure(P=1200),
                        cfwh,
                        state_06 := StatePure(x=0),
                        trap := Trap(),
                        state_07 := StatePure(),
                        ofwh]

        flow_c = Flow(water)
        flow_c.items = [turbine,
                        state_10 := StatePure(P=600),
                        ofwh]

        flow_d = Flow(water)
        flow_d.items = [turbine,
                        state_11 := StatePure(P=10),
                        condenser := Condenser(),
                        state_01 := StatePure(x=0),
                        pump1 := Pump(),
                        state_02 := StatePure(),
                        ofwh]

        cycle = Cycle()
        cycle.flows = [flow_a,
                       flow_b,
                       flow_c,
                       flow_d]
        cycle.netPower = 400000

        cycle.solve()

        for e in cycle._equations:
            e.update()
        cycle.solve()
        for e in cycle._equations:
            e.update()
        cycle.solve()

        self.assertTrue(isWithin(cycle.netPower/cycle.Q_in, 1, '%', 0.452))
        self.assertTrue(isWithin(cycle._get_mainFlow().massFR, 1, '%', 313))
        self.assertTrue(isWithin(flow_b.massFF, 4, '%', 0.05404))
        self.assertTrue(isWithin(flow_c.massFF, 4, '%', 0.1694))

        pass

    def test_flows_water_06(self):
        # CENGEL P10-48
        # diagram in book is not helpful - see solutions

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.items = [mixc := MixingChamber(),
                        state_t := StatePure(),
                        condenser := Condenser(),
                        state_1 := StatePure(x=0),
                        pump := Pump(),
                        state_2 := StatePure(),
                        cfwh := HeatExchanger(),
                        state_3 := StatePure(T=water.define(StatePure(P=1000, x=0)).T),
                        boiler := Boiler(),
                        state_4 := StatePure(P=3000, T=350),
                        turbine := Turbine()]

        flow_b = Flow(water)
        flow_b.items = [turbine,
                        state_5 := StatePure(P=1000),
                        cfwh,
                        state_7 := StatePure(x=0),
                        trap := Trap(),
                        state_8 := StatePure(P=20),
                        mixc]

        flow_c = Flow(water)
        flow_c.items = [turbine,
                        state_6 := StatePure(),
                        mixc]


        cycle = Cycle()
        cycle.flows = [flow_a, flow_b, flow_c]
        cycle.solve()

        for e in cycle._equations:
            e.update()
        cycle.solve()
        for e in cycle._equations:
            e.update()
        cycle.solve()

        for f in cycle.flows:   # TODO - Has to solve the flows manually again
            f.solve()

        for e in cycle._equations:
            e.update()
        cycle.solve()

        self.CompareResults(state_2, {'h': 254.45}, 2)
        self.CompareResults(state_4, {'h': 3116.1, 's': 6.7450}, 2)
        self.CompareResults(state_5, {'h': 2851.9}, 2)
        self.CompareResults(state_6, {'h': 2221.7, 'x': 0.8357}, 2)
        self.CompareResults(state_7, {'h': 762.51, 'T': 179.9}, 2)
        self.CompareResults(flow_b, {'massFF': 0.2437}, 2)

        self.assertTrue(isWithin(cycle.sHeat, 2, '%', 2353))
        self.assertTrue(isWithin(cycle.net_sPower, 2, '%', 737.8))
        self.assertTrue(isWithin(cycle.efficiency, 1, '%', 0.3136))

        pass

    def test_flows_water_07(self):
        # CENGEL P10-55

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.items = [ofwh := MixingChamber(),
                        state_03 := StatePure(x=0),
                        pump2 := Pump(),
                        state_04 := StatePure(),
                        rhboiler := ReheatBoiler(),
                        state_05 := StatePure(P=10000, T=550),
                        turba := Turbine(),
                        state_06 := StatePure(P=800)]

        flow_b = Flow(water)
        flow_b.items = [state_06,
                        rhboiler,
                        state_07 := StatePure(T=500),
                        turbineb := Turbine(),
                        state_08 := StatePure(P=10),
                        condenser := Condenser(),
                        state_01 := StatePure(x=0),
                        pump1 := Pump(),
                        state_02 := StatePure(),
                        ofwh]

        flow_c = Flow(water)
        flow_c.items = [state_06,
                        ofwh]

        cycle = Cycle()
        cycle.flows = [flow_a, flow_b, flow_c]
        cycle.netPower = 80000

        cycle.solve()

        for e in cycle._equations:
            e.update()
        cycle.solve()

        self.CompareResults(state_02, {'h': 192.61}, 2)
        self.CompareResults(state_03, {'h': 720.87, 'mu': 0.001115}, 2)
        self.CompareResults(state_04, {'h': 731.12}, 2)
        self.CompareResults(state_05, {'h': 3502, 's': 6.7585}, 2)
        self.CompareResults(state_06, {'h': 2812.1}, 2)
        self.CompareResults(state_07, {'h': 3481.3, 's': 7.8692}, 2)
        self.CompareResults(state_08, {'h': 2494.7, 'x': 0.9627}, 2)

        self.CompareResults(flow_c, {'massFF': 0.2017}, 2)

        self.assertTrue(isWithin(flow_a.massFR, 2, '%', 54.5))
        self.assertTrue(isWithin(cycle.netPower/cycle.Q_in, 2, '%', 0.444))

        pass

    def test_flows_water_08(self):
        # CENGEL P10-34

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.items = [state_1 := StatePure(x=0),
                        pump := Pump(),
                        state_2 := StatePure(P=5000),
                        rhboiler := ReheatBoiler(infer_fixed_exitT=False),
                        state_3 := StatePure(),
                        hpt := Turbine(),
                        state_4 := StatePure(P=1200, x=0.96),
                        rhboiler,
                        state_5 := StatePure(),
                        lpt := Turbine(),
                        state_6 := StatePure(P=20, x=0.96),
                        condenser := Condenser(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()

        self.CompareResults(state_2, {'h': 256.49}, 2)
        self.CompareResults(state_3, {'h': 3006.9, 'T': 327.2}, 2)
        self.CompareResults(state_5, {'h': 3436, 'T': 481.1}, 2)

        self.assertTrue(isWithin(flow_a.get_sHeatSupplied(), 2, '%', 3482))
        self.assertTrue(isWithin(flow_a.get_net_sWorkExtracted() / flow_a.get_sHeatSupplied(), 2, '%', 0.35))

        pass

    def test_flows_water_09(self):
        # CENGEL P10-35

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.massFR = 12
        flow_a.items = [state_1 := StatePure(x=0),
                        pump := Pump(),
                        state_2 := StatePure(P=15000),
                        rhboiler := ReheatBoiler(infer_fixed_exitT=True),
                        state_3 := StatePure(T=500),
                        hpt := Turbine(),
                        state_4 := StatePure(),
                        rhboiler,
                        state_5 := StatePure(),
                        lpt := Turbine(),
                        state_6 := StatePure(P=10, x=0.9),
                        condenser := Condenser(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()

        self.CompareResults(state_2, {'h': 206.95}, 2)
        self.CompareResults(state_5, {'P': 2160, 'h': 3466.61}, 2)  # not sure why answers say 2150 - did manually, ~2161
        self.CompareResults(state_4, {'h': 2817.2}, 2)

        self.assertTrue(isWithin(cycle.Q_in, 2, '%', 45039))
        self.assertTrue(isWithin(cycle.netPower / cycle.Q_in, 2, '%', 0.426))

        pass

    def test_flows_water_10(self):
        # CENGEL P10-37

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.items = [state_1 := StatePure(x=0, P=10),
                        pump := Pump(eta_isentropic=0.95),
                        state_2 := StatePure(),
                        rhboiler := ReheatBoiler(infer_fixed_exitT=True),
                        state_3 := StatePure(P=10000, T=500),
                        hpt := Turbine(eta_isentropic=0.8),
                        state_4 := StatePure(),
                        rhboiler,
                        state_5 := StatePure(P=1000, T=500),
                        lpt := Turbine(eta_isentropic=0.8),
                        state_6 := StatePure(),
                        condenser := Condenser(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.netPower = 80000
        cycle.solve()

        self.CompareResults(state_2, {'h': 202.43}, 2)
        self.CompareResults(state_4, {'h': 2902}, 2)
        self.CompareResults(state_6, {'h': 2664.8, 'T': 88.1}, 2)

        self.assertTrue(isWithin(flow_a.get_net_sWorkExtracted(), 2, '%', 1276.8))
        self.assertTrue(isWithin(flow_a.get_sHeatSupplied(), 2, '%', 3749.8))
        self.assertTrue(isWithin(flow_a.massFR, 2, '%', 62.7))

        pass

    def test_flows_water_11(self):
        # CENGEL P10-38

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.items = [state_1 := StatePure(x=0, P=10),
                        pump := Pump(eta_isentropic=1),
                        state_2 := StatePure(),
                        rhboiler := ReheatBoiler(infer_fixed_exitT=True),
                        state_3 := StatePure(P=10000, T=500),
                        hpt := Turbine(eta_isentropic=1),
                        state_4 := StatePure(),
                        rhboiler,
                        state_5 := StatePure(P=1000, T=500),
                        lpt := Turbine(eta_isentropic=1),
                        state_6 := StatePure(),
                        condenser := Condenser(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.netPower = 80000
        cycle.solve()

        self.CompareResults(state_6, {'x': 0.949}, 2)

        self.assertTrue(isWithin(flow_a.get_net_sWorkExtracted() / flow_a.get_sHeatSupplied(), 2, '%', 0.413))
        self.assertTrue(isWithin(flow_a.massFR, 2, '%', 50))

        pass

    def test_flows_water_12(self):
        # CENGEL P10-45

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.items = [ofwh:= MixingChamber(),
                        state_3 := StatePure(x=0),
                        pump2 := Pump(),
                        state_4 := StatePure(),
                        boiler := Boiler(),
                        state_5 := StatePure(P=6000, T=450),
                        turbine := Turbine()]

        flow_b = Flow(water)
        flow_b.items = [turbine,
                        state_6 := StatePure(P=400),
                        ofwh]

        flow_c = Flow(water)
        flow_c.items = [turbine,
                        state_7 := StatePure(P=20),
                        condenser := Condenser(),
                        state_1 := StatePure(x=0),
                        pump1 := Pump(),
                        state_2 := StatePure(),
                        ofwh]

        cycle = Cycle()
        cycle.flows = [flow_a, flow_b, flow_c]
        cycle.solve()
        cycle.solve()

        for e in cycle._equations:
            e.update()

        cycle.solve()

        self.assertTrue(isWithin(cycle.net_sPower, 1, '%', 1017))
        self.assertTrue(isWithin(cycle.efficiency, 1, '%', 0.378))

        pass

    def test_flows_water_13(self):
        # CENGEL P10-46

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.items = [mixc := MixingChamber(),
                        state_4 := StatePure(),
                        boiler := Boiler(),
                        state_5 := StatePure(P=6000, T=450),
                        turbine := Turbine()]

        flow_b = Flow(water)
        flow_b.items = [turbine,
                        state_6 := StatePure(P=400),
                        cfwh := HeatExchanger(),
                        state_3 := StatePure(x=0),
                        pump2 := Pump(),
                        state_9 := StatePure(),
                        mixc]

        flow_c = Flow(water)
        flow_c.items = [turbine,
                        state_7 := StatePure(),
                        condenser := Condenser(),
                        state_1 := StatePure(x=0, P=20),
                        pump1 := Pump(),
                        state_2 := StatePure(),
                        cfwh,
                        state_8 := StatePure(),
                        mixc]

        # assuming h8 = h9 = h4 - 8 & 9 have same pressure. determine 8's h by vdp (determine out of nowhere)

        cycle = Cycle()
        cycle.flows = [flow_a, flow_b, flow_c]
        cycle.solve()


        wtot = 0
        for f in cycle.flows:
            wtot += f.massFF * f.get_net_sWorkExtracted()

        qtot = 0
        for f in cycle.flows:
            qtot += f.massFF * f.get_sHeatSupplied()

        self.assertTrue(isWithin(wtot, 1, '%', 1016.8))
        self.assertTrue(isWithin(wtot / qtot, 1, '%', 0.378))

        pass

    def test_flows_water_14(self):

        # CENGEL P10-47

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.massFR = 16
        flow_a.items = [ofwh2 := MixingChamber(),
                        state_05 := StatePure(x=0),
                        pump3 := Pump(),
                        state_06 := StatePure(),
                        boiler := Boiler(),
                        state_07 := StatePure(P=8000, T=550),
                        turbine := Turbine()]

        flow_b = Flow(water)
        flow_b.items = [turbine,
                        state_08 := StatePure(P=600),
                        ofwh2]

        flow_c = Flow(water)
        flow_c.items = [turbine,
                        state_09 := StatePure(P=200),
                        ofwh1 := MixingChamber()]

        flow_d = Flow(water)
        flow_d.items = [turbine,
                        state_10 := StatePure(P=10),
                        condenser := Condenser(),
                        state_01 := StatePure(x=0),
                        pump1 := Pump(),
                        state_02 := StatePure(),
                        ofwh1]

        flow_e = Flow(water)
        flow_e.items = [ofwh1,
                        state_03 := StatePure(x=0),
                        pump2 := Pump(),
                        state_04 := StatePure(),
                        ofwh2]


        cycle = Cycle()
        cycle.flows = [flow_a, flow_b, flow_c, flow_d, flow_e]
        cycle.solve()

        for e in cycle._equations:
            e.update()
        cycle.solve()

        for e in cycle._equations:
            e.update()
        cycle.solve()

        self.CompareResults(state_02, {'h': 192}, 2)
        self.CompareResults(state_04, {'h': 505.13}, 2)
        self.CompareResults(state_06, {'h': 678.52}, 2)
        self.CompareResults(flow_b, {'massFF': 0.07171}, 2)
        self.CompareResults(flow_c, {'massFF': 0.1201}, 2)

        self.assertTrue(isWithin(cycle.netPower, 1, '%', 19800))
        self.assertTrue(isWithin(cycle.efficiency, 1, '%', 0.435))

        pass

    def test_flows_water_15(self):

        # CENGEL P10-22

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.massFR = 20
        flow_a.items = [state_01 := StatePure(P=6000),
                        boiler := Boiler(),
                        state_02 := StatePure(T=450),
                        turbine := Turbine(eta_isentropic=0.94),
                        state_03 := StatePure(),
                        condenser := Condenser(),
                        state_04 := StatePure(P=50, T=water.define(StatePure(P=50, x=0)).T - 6.3),
                        pump := Pump(),
                        state_01]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()

        self.CompareResults(state_04, {'h': 314.03, 'mu': 0.001026}, 2)
        self.CompareResults(state_01, {'h': 320.13}, 2)
        self.CompareResults(state_03, {'h': 2394.4}, 2)

        self.assertTrue(isWithin(cycle.Q_in, 1, '%', 59660))
        self.assertTrue(isWithin(cycle.netPower, 1, '%', 18050))
        self.assertTrue(isWithin(cycle.efficiency, 1, '%', 0.303))

        pass

    def test_flows_water_16(self):
        # CENGEL P10-30

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.massFR = 1.74
        flow_a.items = [state_02 := StatePure(),
                        rhboiler := ReheatBoiler(infer_fixed_exitT=True),
                        state_03 := StatePure(T=450, P=15000),
                        hpturbine := Turbine(),
                        state_04 := StatePure(P=2000),
                        rhboiler,
                        state_05 := StatePure(),
                        lpturbine := Turbine(),
                        state_06 := StatePure(P=100),
                        condenser := Condenser(),
                        state_01 := StatePure(x=0),
                        pump := Pump(),
                        state_02]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()

        self.CompareResults(state_02, {'h': 433.05}, 2)
        self.CompareResults(state_06, {'h': 2648}, 2)

        self.assertTrue(isWithin(cycle.sHeat, 1, '%', 3379.8))
        self.assertTrue(isWithin(cycle.net_sPower, 1, '%', 1149.2))
        self.assertTrue(isWithin(cycle.efficiency, 1, '%', 0.340))

        pass

    def test_flows_water_17(self):
        # CENGEL P10-31

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.massFR = 1.74
        flow_a.items = [state_02 := StatePure(),
                        rhboiler := ReheatBoiler(infer_fixed_exitT=True),
                        state_03 := StatePure(T=400, P=6000),
                        hpturbine := Turbine(),
                        state_04 := StatePure(P=2000),
                        rhboiler,
                        state_05 := StatePure(),
                        lpturbine := Turbine(),
                        state_06 := StatePure(P=20),
                        condenser := Condenser(),
                        state_01 := StatePure(x=0),
                        pump := Pump(),
                        state_02]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()

        self.CompareResults(state_02, {'h': 257.5}, 2)
        self.CompareResults(state_06, {'h': 2349.7}, 2)

        self.assertTrue(isWithin(cycle.sHeat, 1, '%', 3268))
        self.assertTrue(isWithin(cycle.net_sPower, 1, '%', 1170))
        self.assertTrue(isWithin(cycle.efficiency, 1, '%', 0.358))

        pass

    def test_flows_water_17(self):
        # CENGEL Ex10-6

        flow_a = Flow(water)
        flow_a.massFF = 1
        flow_a.items = [mixc := MixingChamber(),
                        state_08 := StatePure(),
                        rhboiler := ReheatBoiler(),
                        state_09 := StatePure(P=15000, T=600),
                        hpt := Turbine(),
                        state_10 := StatePure(P=4000)]

        flow_b = Flow(water)
        flow_b.items = [state_10,  # diverging flows at pipe - no device
                        rhboiler,
                        state_11 := StatePure(T=600),
                        lpt := Turbine()]

        flow_c = Flow(water)
        flow_c.items = [state_10,
                        cfwh := HeatExchanger(infer_common_exitT=True),
                        state_06 := StatePure(x=0),
                        pump3 := Pump(),
                        state_07 := StatePure(),
                        mixc]

        flow_d = Flow(water)
        flow_d.items = [lpt,
                        state_12 := StatePure(P=500),
                        ofwh := MixingChamber()]

        flow_e = Flow(water)
        flow_e.items = [lpt,
                        state_13 := StatePure(P=10),
                        condenser := Condenser(),
                        state_01 := StatePure(x=0),
                        pump1 := Pump(),
                        state_02 := StatePure(),
                        ofwh]

        flow_f = Flow(water)
        flow_f.items = [ofwh,
                        state_03 := StatePure(x=0),
                        pump2 := Pump(),
                        state_04 := StatePure(),  # h4 wrong in book?
                        cfwh,
                        state_05 := StatePure(),
                        mixc]

        cycle = Cycle()
        cycle.flows = [flow_a, flow_b, flow_c, flow_d, flow_e, flow_f]
        cycle.solve()

        for e in cycle._equations:
            e.update()
        cycle.solve()

        for e in cycle._equations:
            e.update()
        cycle.solve()

        self.CompareResults(flow_c, {'massFF': 0.1766}, 3)
        self.CompareResults(flow_d, {'massFF': 0.1306}, 3)

        self.assertTrue(isWithin(cycle.efficiency, 1, '%', 0.492))
        self.assertTrue(isWithin(cycle.sHeat, 1, '%', 2921.4))

        pass

        # CENGEL P10-36
        # TODO - NEED TO TRY/ERROR & CONSTRUCT LARGER SCOPE EQUATIONS - Isentropic efficiency
        # flow_a = Flow(water)
        # flow_a.massFF = 1
        # flow_a.massFR = 7.7
        # flow_a.items = [state_1 := StatePure(x=0),
        #                 pump := Pump(eta_isentropic=0.9),
        #                 state_2 := StatePure(P=12500),
        #                 rhboiler := ReheatBoiler(infer_fixed_exitT=True),
        #                 state_3 := StatePure(T=550),
        #                 hpt := Turbine(eta_isentropic=0.85),
        #                 state_4 := StatePure(P=2000),
        #                 rhboiler,
        #                 state_5 := StatePure(T=450),
        #                 lpt := Turbine(eta_isentropic=0.85),
        #                 state_6 := StatePure(x=0.95),
        #                 condenser := Condenser(),
        #                 state_1]
        #
        # cycle = Cycle()
        # cycle.flows = [flow_a]
        # cycle.solve()
        #
        # pass

        # # CENGEL P10-56
        #
        # flow_a = Flow(water)
        # flow_a.massFF = 1
        # flow_a.items = [mixc := MixingChamber(),
        #                 state_04 := StatePure(),
        #                 rhboiler := ReheatBoiler(),
        #                 state_05 := StatePure(P=10000, T=550),
        #                 hpt := Turbine()]
        #
        # flow_b = Flow(water)
        # flow_b.items = [hpt,
        #                 state_06 := StatePure(P=800),
        #                 cfwh := HeatExchanger(),
        #                 state_03 := StatePure(P=800, x=0),
        #                 pump2 := Pump(),
        #                 state_10 := StatePure(),
        #                 mixc]
        #
        # flow_c = Flow(water)
        # flow_c.items = [hpt,
        #                 state_06,
        #                 rhboiler,
        #                 state_07 := StatePure(T=500),
        #                 lpt := Turbine(),
        #                 state_08 := StatePure(),
        #                 condenser := Condenser(),
        #                 state_01 := StatePure(P=10, x=0),
        #                 pump1 := Pump(),
        #                 state_02 := StatePure(),
        #                 cfwh,
        #                 state_09 := StatePure(),
        #                 mixc]
        #
        # cycle = Cycle()
        # cycle.flows = [flow_a, flow_b, flow_c]
        #
        # cycle.solve()
        # for e in cycle._equations:
        #     e.update()
        # cycle.solve()
        #
        # pass

    def test_flows_refr_01(self):
        # CENGEL P11-13

        flow_a = Flow(R134a)
        flow_a.massFF = 1
        flow_a.items = [state_1 := StatePure(x=1),
                        compressor := Compressor(),
                        state_2 := StatePure(P=800),
                        condenser := Condenser(),
                        state_3 := StatePure(x=0),
                        expValve := Trap(),
                        state_4 := StatePure(T=-12),
                        evaporator := Boiler(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.Q_in = 150
        cycle.solve()


    def test_flows_air_01(self):
        # MECH2201 - A11-3

        flow_a = Flow(air, massFlowFraction=1)
        flow_a.items = [state_1 := StateIGas(P=150, T=20),
                        comp1 := Compressor(eta_isentropic=0.82),
                        state_2 := StateIGas(P=300),
                        intercooler := Intercooler(coolTo='ideal'),
                        state_3 := StateIGas(T=20),
                        comp2 := Compressor(eta_isentropic=0.82),
                        state_4 := StateIGas(P=600),
                        regenerator := Regenerator(effectiveness=0.7, counterFlow_commonColdTemperature=True),
                        state_5 := StateIGas(),
                        combustor := Combustor(),
                        state_6 := StateIGas(T=750),
                        turb1 := Turbine(eta_isentropic=0.82),
                        state_7 := StateIGas(P=300),
                        reheat := GasReheater(heatTo='ideal'),
                        state_8 := StateIGas(T=750),
                        turb2 := Turbine(eta_isentropic=0.82),
                        state_9 := StateIGas(),
                        regenerator,
                        state_10 := StateIGas(),
                        exhaust := Exhaust(),
                        state_1]

        flow_a.constant_c = True
        cycle = Cycle()
        cycle.netPower = 350  # kW
        cycle.flows = [flow_a]
        cycle.solve()

        self.CompareResults(state_2, {'T': 98.26}, 3)
        self.CompareResults(state_4, {'T': 98.26}, 3)
        self.CompareResults(state_5, {'T': 448.97}, 3)
        self.CompareResults(state_7, {'T': 599.28}, 3)
        self.CompareResults(state_8, {'T': 750}, 3)
        self.CompareResults(state_9, {'T': 599.28}, 3)
        self.assertTrue(isWithin(cycle.efficiency, 1, '%', 0.321))

    def test_flows_air_02(self):
        # MECH2201 - A11-2
        # Cengel P9-123

        flow_a = Flow(air, massFlowFraction=1)
        flow_a.items = [state_1 := StateIGas(P=100, T=17),
                        compressor1 := Compressor(pressureRatio=5),
                        state_2 := StateIGas(),
                        intercooler := Intercooler(coolTo='ideal'),
                        state_3 := StateIGas(),
                        compressor2 := Compressor(pressureRatio=5),
                        state_4 := StateIGas(),
                        regenerator := Regenerator(),
                        state_5 := StateIGas(),
                        combustor := Combustor(sHeatSupplied=300),
                        state_6 := StateIGas(),
                        turbine1 := Turbine(pressureRatio=5),
                        state_7 := StateIGas(),
                        reheater := GasReheater(heatTo='heatSupplied', sHeatSupplied=300),
                        state_8 := StateIGas(),
                        turbine2 := Turbine(pressureRatio=5),
                        state_9 := StateIGas(),
                        regenerator,
                        state_10 := StateIGas(),
                        exhaust := Exhaust(),
                        state_1]

        flow_a.constant_c = True
        cycle = Cycle()
        cycle.flows = [flow_a]
        eqn = LinearEquation(LHS=[(-1, (state_4, 'T')), (1, (state_5, 'T'))], RHS=20)
        cycle._equations.append(eqn)

        cycle.solve()
        cycle.solve()
        cycle.solve()
        cycle.solve()

        self.CompareResults(state_2, {'T': 459.31-273}, 3)
        self.CompareResults(state_5, {'T': 479.31-273}, 3)
        self.CompareResults(state_6, {'T': 777.82-273}, 3)
        self.CompareResults(state_7, {'T': 491.10-273}, 3)
        self.CompareResults(state_8, {'T': 789.61-273}, 3)
        self.CompareResults(state_9, {'T': 498.55-273}, 3)
        self.assertTrue(isWithin(cycle.efficiency, 3, '%', 0.401))


    def test_flows_air_03(self):
        # MECH2201 - A11-1

        flow_a = Flow(air, massFlowFraction=1)
        flow_a.items = [state_1 := StateIGas(P=100, T=30),
                        compressor1 := Compressor(pressureRatio=12),
                        state_2 := StateIGas(),
                        regenerator := Regenerator(),
                        state_3 := StateIGas(),
                        combustor := Combustor(),
                        state_4 := StateIGas(T=800),
                        turbine1 := Turbine(pressureRatio=12),
                        state_5 := StateIGas(),
                        regenerator,
                        state_6 := StateIGas(),
                        exhaust := Exhaust(),
                        state_1]

        flow_a.constant_c = True
        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.netPower = 115
        eqn = LinearEquation(LHS=[(1, (state_5, 'T')), (-1, (state_3, 'T'))], RHS=10)
        cycle._equations.append(eqn)
        cycle.solve()

        self.CompareResults(state_2, {'T': 616.28-273}, 3)
        self.CompareResults(state_3, {'T': 517.55-273}, 3)
        self.CompareResults(state_5, {'T': 527.55-273}, 3)
        self.CompareResults(state_6, {'T': 626.28-273}, 3)
        self.CompareResults(flow_a, {'massFR': 0.493}, 3)
        self.assertTrue(isWithin(flow_a.sHeatSupplied*flow_a.massFR, 3, '%', 275))


    def test_flows_air_04(self):
        # Cengel P9-90
        # Special: FINDS STATE_IN from STATE_OUT - reverse isentropic efficiency calculation by iteration

        flow_a = Flow(air, massFlowFraction=1)
        flow_a.items = [state_1 := StateIGas(P=100, T=40),
                        compressor1 := Compressor(eta_isentropic=0.85),
                        state_2 := StateIGas(P=1600),
                        combustor := Combustor(),
                        state_3 := StateIGas(),
                        turbine1 := Turbine(eta_isentropic=0.88),
                        state_4 := StateIGas(T=650),
                        exhaust := Exhaust(),
                        state_1]

        apply_IGasLaw(state_1, R=air.R)
        flow_a.massFR = (850/60)/state_1.mu

        flow_a.constant_c = False
        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()

        self.CompareResults(state_2, {'h': 758.6}, 3)
        self.CompareResults(state_4, {'h': 959.2}, 3)
        self.CompareResults(state_3, {'h': 1790, 'T': 1353}, 3)

        self.CompareResults(flow_a, {'massFR': 15.77}, 3)
        self.assertTrue(isWithin(cycle.netPower, 3, '%', 6081))
        self.assertTrue(isWithin(cycle.efficiency, 3, '%', 0.374))

    def test_flows_air_05(self):
        # MECH2201 - A11-2
        # Cengel P9-124

        flow_a = Flow(air, massFlowFraction=1)
        flow_a.items = [state_1 := StateIGas(P=100, T=17),
                        compressor1 := Compressor(pressureRatio=4),
                        state_2 := StateIGas(),
                        intercooler := Intercooler(coolTo='ideal'),
                        state_3 := StateIGas(),
                        compressor2 := Compressor(pressureRatio=4),
                        state_4 := StateIGas(),
                        intercooler2 := Intercooler(coolTo='ideal'),
                        state_5 := StateIGas(),
                        compressor3 := Compressor(pressureRatio=4),
                        state_6 := StateIGas(),
                        regenerator := Regenerator(),
                        state_7 := StateIGas(),
                        combustor := Combustor(sHeatSupplied=300),
                        state_8 := StateIGas(),
                        turbine1 := Turbine(pressureRatio=4),
                        state_9 := StateIGas(),
                        reheater := GasReheater(heatTo='heatSupplied', sHeatSupplied=300),
                        state_10 := StateIGas(),
                        turbine2 := Turbine(pressureRatio=4),
                        state_11 := StateIGas(),
                        reheater2 := GasReheater(heatTo='heatSupplied', sHeatSupplied=300),
                        state_12 := StateIGas(),
                        turbine3 := Turbine(pressureRatio=4),
                        state_13 := StateIGas(),
                        regenerator,
                        state_14 := StateIGas(),
                        exhaust := Exhaust(),
                        state_1]

        flow_a.constant_c = True
        cycle = Cycle()
        cycle.flows = [flow_a]
        eqn = LinearEquation(LHS=[(-1, (state_6, 'T')), (1, (state_7, 'T'))], RHS=20)
        cycle._equations.append(eqn)

        cycle.solve()  # TODO - cycle solution should redo equations on its own.
        cycle.solve()
        cycle.solve()
        cycle.solve()
        cycle.solve()

        self.CompareResults(state_2, {'T': 430.9-273}, 3)
        self.CompareResults(state_4, {'T': 430.9-273}, 3)
        self.CompareResults(state_6, {'T': 430.9-273}, 3)
        self.CompareResults(state_7, {'T': 450.9-273}, 3)
        self.CompareResults(state_8, {'T': 749.4-273}, 3)
        self.CompareResults(state_9, {'T': 504.3-273}, 3)
        self.CompareResults(state_10, {'T': 802.8-273}, 3)
        self.CompareResults(state_11, {'T': 540.2-273}, 3)
        self.CompareResults(state_12, {'T': 838.7-273}, 3)
        self.CompareResults(state_13, {'T': 564.4-273}, 3)
        self.CompareResults(state_14, {'T': 544.4-273}, 3)
        self.assertTrue(isWithin(cycle.sHeat, 3, '%', 900))
        self.assertTrue(isWithin(cycle.efficiency, 3, '%', 0.401))

    def test_flows_air_06(self):
        # Cengel P9-121
        PR = 3
        flow_a = Flow(workingFluid=air, massFlowFraction=1)
        flow_a.constant_c = False
        flow_a.items = [state_1 := StateIGas(T=300-273, P=100),  # Dummy pressure. TODO: Could use PRatio where possible, that way, won't need dummy P
                        compressor1 := Compressor(pressureRatio=PR),
                        state_2 := StateIGas(),
                        intercooler := Intercooler(coolTo='ideal'),
                        state_3 := StateIGas(),
                        compressor2 := Compressor(pressureRatio=PR),
                        state_4 := StateIGas(),
                        regenerator := Regenerator(effectiveness=0.75, counterFlow_commonColdTemperature=True),
                        state_9 := StateIGas(),
                        combustor := Combustor(),
                        state_5 := StateIGas(T=1200-273),
                        turbine1 := Turbine(pressureRatio=PR),
                        state_6 := StateIGas(),
                        reheater := GasReheater(heatTo='ideal'),
                        state_7 := StateIGas(),
                        turbine2 := Turbine(pressureRatio=PR),
                        state_8 := StateIGas(),
                        regenerator,
                        state_10 := StateIGas(),
                        exhaust := Exhaust(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()
        cycle.solve()

        self.CompareResults(state_2, {'h': 411.26, 'P_r': 4.158}, 3)
        self.CompareResults(state_4, {'h': 411.26}, 3)
        self.CompareResults(state_5, {'h': 1277.79, 'P_r': 238}, 3)
        self.CompareResults(state_6, {'h': 946.36}, 3)
        self.CompareResults(state_8, {'h': 946.36}, 3)
        self.CompareResults(flow_a, {'net_sWorkExtracted': 440.72}, 3)
        self.assertTrue(isWithin(regenerator.effectiveness*(state_8.h - state_4.h), 3, '%', 401.33))
        self.assertTrue(isWithin(cycle.efficiency, 3, '%', 0.553))

    def test_flows_air_07(self):
        # Cengel P9-109

        flow_a = Flow(workingFluid=air, massFlowFraction=1)
        flow_a.constant_c = False

        flow_a.items = [state_1 := StateIGas(T=310-273, P=100),
                        compressor := Compressor(),
                        state_2 := StateIGas(P=900, T=650-273),
                        regenerator := Regenerator(effectiveness=0.8, counterFlow_commonColdTemperature=True),
                        state_5 := StateIGas(),
                        combustor := Combustor(),
                        state_3 := StateIGas(T=1400-273),
                        turbine := Turbine(eta_isentropic=0.9),
                        state_4 := StateIGas(),
                        regenerator,
                        state_6 := StateIGas(),
                        exhaust := Exhaust(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()
        cycle.solve()

        self.CompareResults(state_4, {'h': 900.74}, 3)
        self.assertTrue(isWithin(cycle.net_sPower, 3, '%', 265.08))
        self.assertTrue(isWithin(cycle.sHeat, 3, '%', 662.88))

        self.assertTrue(isWithin(state_5.h - state_2.h, 3, '%', 192.7))
        self.assertTrue(isWithin(cycle.efficiency, 3, '%', 0.4))

    def test_flows_air_08(self):
        # Cengel P9-104

        flow_a = Flow(workingFluid=air, massFlowFraction=1)
        flow_a.constant_c = False

        flow_a.items = [state_1 := StateIGas(T=300-273, P=100),
                        compressor := Compressor(pressureRatio=10),
                        state_2 := StateIGas(),
                        regenerator := Regenerator(effectiveness=1, counterFlow_commonColdTemperature=True),
                        state_5 := StateIGas(),
                        combustor := Combustor(),
                        state_3 := StateIGas(T=1200-273),
                        turbine := Turbine(pressureRatio=10),
                        state_4 := StateIGas(),
                        regenerator,
                        state_6 := StateIGas(),
                        exhaust := Exhaust(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()
        cycle.solve()

        self.CompareResults(state_2, {'h': 579.87}, 3)
        self.CompareResults(state_4, {'h': 675.85}, 3)

        self.assertTrue(isWithin(cycle.net_sPower, 3, '%', 322.26))
        self.assertTrue(isWithin(cycle.sHeat, 3, '%', 601.94))
        self.assertTrue(isWithin(cycle.efficiency, 3, '%', 0.535))

    def test_flows_air_09(self):
        # Cengel P9-83

        flow_a = Flow(workingFluid=air, massFlowFraction=1)
        flow_a.constant_c = False

        flow_a.items = [state_1 := StateIGas(T=295-273, P=100),
                        compressor := Compressor(pressureRatio=10, eta_isentropic=0.83),
                        state_2 := StateIGas(),
                        combustor := Combustor(),
                        state_3 := StateIGas(T=1240- 273),
                        turbine := Turbine(pressureRatio=10, eta_isentropic=0.87),
                        state_4 := StateIGas(),
                        exhaust := Exhaust(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()

        self.CompareResults(state_2, {'h': 626.6}, 3)
        self.CompareResults(state_4, {'h': 783.04, 'T':764.4-273}, 3)

        self.assertTrue(isWithin(cycle.net_sPower, 3, '%', 210.4))
        self.assertTrue(isWithin(cycle.sHeat, 3, '%', 698.3))
        self.assertTrue(isWithin(cycle.efficiency, 3, '%', 0.301))

    def test_flows_air_10(self):
        # Cengel P9-85

        flow_a = Flow(workingFluid=air, massFlowFraction=1)
        flow_a.constant_c = True

        flow_a.items = [state_1 := StateIGas(T=295-273, P=100),
                        compressor := Compressor(pressureRatio=10, eta_isentropic=0.83),
                        state_2 := StateIGas(),
                        combustor := Combustor(),
                        state_3 := StateIGas(T=1240- 273),
                        turbine := Turbine(pressureRatio=10, eta_isentropic=0.87),
                        state_4 := StateIGas(),
                        exhaust := Exhaust(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.solve()

        self.CompareResults(state_2, {'T': 625.8-273}, 3)
        self.CompareResults(state_4, {'T': 720-273}, 3)

        self.assertTrue(isWithin(cycle.net_sPower, 3, '%', 190.2))
        self.assertTrue(isWithin(cycle.sHeat, 3, '%', 617.3))
        self.assertTrue(isWithin(cycle.efficiency, 3, '%', 0.308))

    def test_flows_air_11(self):
        # Cengel P9-94

        flow_a = Flow(workingFluid=air, massFlowFraction=1)
        flow_a.constant_c = True

        flow_a.items = [state_1 := StateIGas(T=0, P=100),
                        compressor := Compressor(pressureRatio=8),
                        state_2 := StateIGas(),
                        combustor := Combustor(),
                        state_3 := StateIGas(T=1500 - 273),
                        hpturbine := Turbine(),
                        state_4 := StateIGas(),
                        lpturbine := Turbine(),
                        state_5 := StateIGas(),
                        exhaust := Exhaust(),
                        state_1]

        cycle = Cycle()
        cycle.flows = [flow_a]
        cycle.netPower = 200000
        eqn = LinearEquation(LHS=[(1, (state_2, 'T')), (-1, (state_1, 'T')), (-1, (state_3, 'T')), (1, (state_4, 'T'))], RHS=0)
        cycle._equations.append(eqn)
        cycle.solve()
        cycle.solve()

        self.CompareResults(state_4, {'T': 1279-273, 'P': 457}, 3)
        self.CompareResults(flow_a, {'massFR': 442}, 3)
