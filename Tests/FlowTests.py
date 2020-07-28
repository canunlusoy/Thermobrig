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

        flow = Flow(workingFluid=water)
        flow.items = [StatePure(P=10000, T=500),
                      Turbine(eta_isentropic=0.8),
                      StatePure(P=1000),
                      rhboiler := Boiler(outletTemperature_fixed=500),
                      StatePure(T=500),
                      Turbine(eta_isentropic=0.8),
                      StatePure(),
                      Condenser(),
                      StatePure(P=10, x=0),
                      Pump(eta_isentropic=0.95),
                      StatePure(),
                      rhboiler]