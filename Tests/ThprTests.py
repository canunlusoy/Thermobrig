import unittest

from ThermalProperties.States import StatePure
from ThermalProperties.ThprOps import fullyDefine_StatePure

from Utilities.FileOps import read_Excel_DF, process_MaterialPropertyDF
from Utilities.Numeric import isWithin

dataFile_path = r'D:\Belgeler\İşler\Thermobrig\Thermodynamic Property Data\Cengel_Formatted_Unified.xlsx'
dataFile_worksheet = 'WaterUnified'
dataFile = read_Excel_DF(dataFile_path, worksheet=dataFile_worksheet, headerRow=1, skipRows=[0])
MaterialPropertyDF = process_MaterialPropertyDF(dataFile)


class TestStateDefineMethods_Water(unittest.TestCase):

    def test_satMix_01(self):
        # From MECH2201 - A9 Q3

        statePropt = {'P': 6, 's': 6.4855, 'x': 0.7638}
        testState = StatePure(**statePropt)
        self.assertTrue(testState.isFullyDefinable())
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected = 1996.7
        self.assertTrue(isWithin(testState.h, 3, '%', expected))
        print('Received: {0}'.format(testState.h))
        print('Expected: {0}'.format(expected))

    def test_satMix_02(self):
        # From MECH2201 - A9 Q2 - state 4

        statePropt = {'P': 5, 's': 7.7622, 'x': 0.92}
        testState = StatePure(**statePropt)
        self.assertTrue(testState.isFullyDefinable())
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected = 2367.8
        self.assertTrue(isWithin(testState.h, 3, '%', expected))
        print('Received: {0}'.format(testState.h))
        print('Expected: {0}'.format(expected))

    def test_satMix_03(self):
        # From MECH2201 - A9 Q1 - state 4

        statePropt = {'P': 10, 'x': 0.9483}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_s = 7.7622
        expected_h = 2460.9

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Received: {0}'.format(testState.h))
        print('Expected: {0}'.format(expected_h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Received: {0}'.format(testState.s))
        print('Expected: {0}'.format(expected_s))



    def test_satLiq_01(self):
        # From MECH2201 - A9 Q2 - state 11

        statePropt = {'P': 600, 'x': 0}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected = 670.56
        self.assertTrue(isWithin(testState.h, 3, '%', expected))
        print('Received: {0}'.format(testState.h))
        print('Expected: {0}'.format(expected))


    def test_satLiq_02(self):
        # From MECH2201 - A9 Q2 - state 7

        statePropt = {'P': 200, 'x': 0}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 504.7
        expected_mu = 0.001061
        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Received: {0}'.format(testState.h))
        print('Expected: {0}'.format(expected_h))

        self.assertTrue(isWithin(testState.mu, 3, '%', expected_mu))
        print('Received: {0}'.format(testState.mu))
        print('Expected: {0}'.format(expected_mu))

    def test_satLiq_03(self):
        # From MECH2201 - A9 Q1 - state 5

        statePropt = {'P': 10, 'x': 0}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 191.83
        expected_mu = 0.001010
        expected_s = 0.6493
        expected_T = 45.81

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Received: {0}'.format(testState.h))
        print('Expected: {0}'.format(expected_h))

        self.assertTrue(isWithin(testState.mu, 3, '%', expected_mu))
        print('Received: {0}'.format(testState.mu))
        print('Expected: {0}'.format(expected_mu))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Received: {0}'.format(testState.s))
        print('Expected: {0}'.format(expected_s))

        self.assertTrue(isWithin(testState.T, 3, '%', expected_T))
        print('Received: {0}'.format(testState.T))
        print('Expected: {0}'.format(expected_T))