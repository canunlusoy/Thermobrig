import unittest

from typing import Dict, Union

from Models.Flows import Flow
from Models.States import StatePure, StateIGas
from Models.Devices import Turbine, Boiler, Condenser, Pump
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

    def test_flows_01(self):
        # From MECH2201 - A9 Q1
        # Net power = 80 MW
        # x after Turbine, mass flow rate, thermal efficiency?

        flow = Flow(workingFluid=water)
        flow.items = [StatePure(P=10000, T=500),  # State 0
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
                      rhboiler]

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
