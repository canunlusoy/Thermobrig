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
        print('Expected: {0}'.format(expected))
        print('Received: {0}'.format(testState.h))

    def test_satMix_02(self):
        # From MECH2201 - A9 Q2 - state 4

        statePropt = {'P': 5, 's': 7.7622, 'x': 0.92}
        testState = StatePure(**statePropt)
        self.assertTrue(testState.isFullyDefinable())
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected = 2367.8
        self.assertTrue(isWithin(testState.h, 3, '%', expected))
        print('Expected: {0}'.format(expected))
        print('Received: {0}'.format(testState.h))

    def test_satMix_03(self):
        # From MECH2201 - A9 Q1 - state 4

        statePropt = {'P': 10, 'x': 0.9483}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_s = 7.7622
        expected_h = 2460.9

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

    def test_satMix_04(self):
        # From MECH2201 - A9 Q3 - state 8

        statePropt = {'P': 1000, 's': 6.4855}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 2732.43
        expected_x = 0.9773

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.x, 3, '%', expected_x))
        print('Expected: {0}'.format(expected_x))
        print('Received: {0}'.format(testState.x))

    def test_satMix_05(self):
        # From MECH2201 - A9 Q3 - state 11

        statePropt = {'P': 150, 's': 6.4855}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 2409.99
        expected_x = 0.8725

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.x, 3, '%', expected_x))
        print('Expected: {0}'.format(expected_x))
        print('Received: {0}'.format(testState.x))


    def test_satLiq_01(self):
        # From MECH2201 - A9 Q2 - state 11

        statePropt = {'P': 600, 'x': 0}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected = 670.56
        self.assertTrue(isWithin(testState.h, 3, '%', expected))
        print('Expected: {0}'.format(expected))
        print('Received: {0}'.format(testState.h))


    def test_satLiq_02(self):
        # From MECH2201 - A9 Q2 - state 7

        statePropt = {'P': 200, 'x': 0}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 504.7
        expected_mu = 0.001061
        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.mu, 3, '%', expected_mu))
        print('Expected: {0}'.format(expected_mu))
        print('Received: {0}'.format(testState.mu))

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
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.mu, 3, '%', expected_mu))
        print('Expected: {0}'.format(expected_mu))
        print('Received: {0}'.format(testState.mu))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

        self.assertTrue(isWithin(testState.T, 3, '%', expected_T))
        print('Expected: {0}'.format(expected_T))
        print('Received: {0}'.format(testState.T))

    def test_suphVap_01(self):
        # From MECH2201 - A9 Q1 - state 1

        statePropt = {'P': 10000, 'T': 500}  # should identify as suphVap
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 3373.7
        expected_s = 6.5966

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

    def test_suphVap_02(self):
        # From MECH2201 - A9 Q1 - state 2

        statePropt = {'P': 1000, 's': 6.5966}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 2807.3
        expected_T = 181.80

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.T, 3, '%', expected_T))
        print('Expected: {0}'.format(expected_T))
        print('Received: {0}'.format(testState.T))

    def test_suphVap_03(self):
        # From MECH2201 - A9 Q1 - state 3

        statePropt = {'P': 1000, 'T': 500}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 3478.5
        expected_s = 7.7622

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

    def test_suphVap_04(self):
        # From MECH2201 - A9 Q2 - state 1

        statePropt = {'P': 15000, 'T': 600}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 3582.3
        expected_s = 6.6776

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

    def test_suphVap_04(self):
        # From MECH2201 - A9 Q2 - state 2

        statePropt = {'P': 1000, 's': 6.6776}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 2820.3

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

    def test_suphVap_05(self):
        # From MECH2201 - A9 Q2 - state 3

        statePropt = {'P': 1000, 'T': 500}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 3478.5
        expected_s = 7.7622

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

    def test_suphVap_06(self):
        # From MECH2201 - A9 Q3 - state 1

        statePropt = {'P': 12000, 'T': 500}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)
        expected_h = 3347.7
        expected_s = 6.4855

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

    def test_suphVap_07(self):
        # No saturated state exists at the P&T

        statePropt = {'P': 30000, 'T': 375}  # P & T above critical values - no saturated mixture exists
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, MaterialPropertyDF)

        expected_h = 1791.9
        expected_s = 3.9313

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

