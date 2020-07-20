import unittest

from typing import Dict, Union, List

from ThermalProperties.States import StatePure
from ThermalProperties.ThprOps import fullyDefine_StatePure

from Utilities.FileOps import read_Excel_DF, process_MaterialPropertyDF
from Utilities.Numeric import isWithin

dataFile_path = r'D:\Belgeler\İşler\Thermobrig\Thermodynamic Property Data\Cengel_Formatted_Unified.xlsx'
dataFile_worksheet = 'WaterUnified'
dataFile = read_Excel_DF(dataFile_path, worksheet=dataFile_worksheet, headerRow=1, skipRows=[0])
water_mpDF = process_MaterialPropertyDF(dataFile)

dataFile = read_Excel_DF(dataFile_path, worksheet='R134aUnified', headerRow=1, skipRows=[0])
R134a_mpDF = process_MaterialPropertyDF(dataFile)

class TestStateDefineMethods_Water(unittest.TestCase):

    def CompareResults(self, testState: StatePure, expected: Dict, ptolerance: Union[float, int]):
        print('\n')
        for parameter in expected:
            assert hasattr(testState, parameter)
            self.assertTrue(isWithin(getattr(testState, parameter), ptolerance, '%', expected[parameter]))
            print('Expected: {0}'.format(expected[parameter]))
            print('Received: {0}'.format(getattr(testState, parameter)))

    def test_satMix_01(self):
        # From MECH2201 - A9 Q3

        statePropt = {'P': 6, 's': 6.4855, 'x': 0.7638}
        testState = StatePure(**statePropt)
        self.assertTrue(testState.isFullyDefinable())
        testState = fullyDefine_StatePure(testState, water_mpDF)
        expected = 1996.7
        self.assertTrue(isWithin(testState.h, 3, '%', expected))
        print('Expected: {0}'.format(expected))
        print('Received: {0}'.format(testState.h))

    def test_satMix_02(self):
        # From MECH2201 - A9 Q2 - state 4

        statePropt = {'P': 5, 's': 7.7622, 'x': 0.92}
        testState = StatePure(**statePropt)
        self.assertTrue(testState.isFullyDefinable())
        testState = fullyDefine_StatePure(testState, water_mpDF)
        expected = 2367.8
        self.assertTrue(isWithin(testState.h, 3, '%', expected))
        print('Expected: {0}'.format(expected))
        print('Received: {0}'.format(testState.h))

    def test_satMix_03(self):
        # From MECH2201 - A9 Q1 - state 4

        statePropt = {'P': 10, 'x': 0.9483}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, water_mpDF)
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
        testState = fullyDefine_StatePure(testState, water_mpDF)
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
        testState = fullyDefine_StatePure(testState, water_mpDF)
        expected_h = 2409.99
        expected_x = 0.8725

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.x, 3, '%', expected_x))
        print('Expected: {0}'.format(expected_x))
        print('Received: {0}'.format(testState.x))

    def test_satMix_06(self):
        # From MECH2201 - A7 Q1 - state 2

        state1Propt = {'T': 100, 'x': 1}
        state1 = StatePure(**state1Propt)
        state1 = fullyDefine_StatePure(state1, water_mpDF)
        expected_s = 7.3549
        expected_P = 101.35
        expected_mu = 1.6729
        expected_u = 2506.5

        self.assertTrue(isWithin(state1.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(state1.s))

        self.assertTrue(isWithin(state1.P, 3, '%', expected_P))
        print('Expected: {0}'.format(expected_P))
        print('Received: {0}'.format(state1.P))

        self.assertTrue(isWithin(state1.mu, 3, '%', expected_mu))
        print('Expected: {0}'.format(expected_mu))
        print('Received: {0}'.format(state1.mu))

        self.assertTrue(isWithin(state1.u, 3, '%', expected_u))
        print('Expected: {0}'.format(expected_u))
        print('Received: {0}'.format(state1.u))

        state2Propt = {'T': 25, 'mu': state1.mu}
        state2 = StatePure(**state2Propt)
        state2 = fullyDefine_StatePure(state2, water_mpDF)
        expected_x = 0.03856
        expected_s = 0.6832
        expected_u = 193.76

        self.assertTrue(isWithin(state2.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(state2.s))

        self.assertTrue(isWithin(state2.x, 3, '%', expected_x))
        print('Expected: {0}'.format(expected_x))
        print('Received: {0}'.format(state2.x))

        self.assertTrue(isWithin(state2.u, 3, '%', expected_u))
        print('Expected: {0}'.format(expected_u))
        print('Received: {0}'.format(state2.u))

    def test_satMix_07(self):
        # From MECH2201 - A7 Q3 - state 2

        statePropt = {'P': 100, 'u': 2217.4}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, water_mpDF)
        expected_s = 6.5236
        expected_x = 0.862

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

        self.assertTrue(isWithin(testState.x, 3, '%', expected_x))
        print('Expected: {0}'.format(expected_x))
        print('Received: {0}'.format(testState.x))

    def test_satLiq_01(self):
        # From MECH2201 - A9 Q2 - state 11

        statePropt = {'P': 600, 'x': 0}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, water_mpDF)
        expected = 670.56
        self.assertTrue(isWithin(testState.h, 3, '%', expected))
        print('Expected: {0}'.format(expected))
        print('Received: {0}'.format(testState.h))


    def test_satLiq_02(self):
        # From MECH2201 - A9 Q2 - state 7

        statePropt = {'P': 200, 'x': 0}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, water_mpDF)
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
        testState = fullyDefine_StatePure(testState, water_mpDF)
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

    def test_satVap_01(self):
        # From MECH2201 - A7 Q3 - state 1

        statePropt = {'P': 600, 'x': 1}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, water_mpDF)
        expected_mu = 0.3157
        expected_s = 6.76
        expected_T = 158.85
        expected_u = 2567.4

        self.assertTrue(isWithin(testState.u, 3, '%', expected_u))
        print('Expected: {0}'.format(expected_u))
        print('Received: {0}'.format(testState.u))

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
        testState = fullyDefine_StatePure(testState, water_mpDF)
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
        testState = fullyDefine_StatePure(testState, water_mpDF)
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
        testState = fullyDefine_StatePure(testState, water_mpDF)
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
        testState = fullyDefine_StatePure(testState, water_mpDF)
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
        testState = fullyDefine_StatePure(testState, water_mpDF)
        expected_h = 2820.3

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

    def test_suphVap_05(self):
        # From MECH2201 - A9 Q2 - state 3

        statePropt = {'P': 1000, 'T': 500}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, water_mpDF)
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
        testState = fullyDefine_StatePure(testState, water_mpDF)
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
        testState = fullyDefine_StatePure(testState, water_mpDF)

        expected_h = 1791.9
        expected_s = 3.9313

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

    def test_suphVap_08(self):
        # Superheated state requiring double interpolation

        statePropt = {'P': 20, 'T': 625}  # P & T above critical values - no saturated mixture exists
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, water_mpDF)

        expected_mu = 33.159

        self.assertTrue(isWithin(testState.mu, 3, '%', expected_mu))
        print('Expected: {0}'.format(expected_mu))
        print('Received: {0}'.format(testState.mu))

    def test_suphVap_09(self):
        # MECH2201 A7 Q2 State 3 & 1 & 2

        statePropt = {'P': 50, 'T': 100}  # P & T above critical values - no saturated mixture exists
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, water_mpDF)

        expected_h = 2682.5
        expected_s = 7.6947

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

        # below is state 1

        statePropt2 = {'P': 3000, 's': testState.s}
        testState2 = StatePure(**statePropt2)
        testState2 = fullyDefine_StatePure(testState2, water_mpDF)

        expected_h = 3854.1

        self.assertTrue(isWithin(testState2.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState2.h))

        self.assertTrue(testState2.x > 1)

        # below is state 2

        statePropt3 = {'P': 500, 's': testState.s}
        testState3 = StatePure(**statePropt3)
        testState3 = fullyDefine_StatePure(testState3, water_mpDF)

        expected_h = 3207.7

        self.assertTrue(isWithin(testState3.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState3.h))

        self.assertTrue(testState2.x > 1)

    def test_suphVap_10(self):
        # MECH2201 A8 Q1 State 1

        statePropt = {'P': 8000, 'T': 500}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, water_mpDF)

        expected_h = 3398.3
        expected_s = 6.7240

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.s, 3, '%', expected_s))
        print('Expected: {0}'.format(expected_s))
        print('Received: {0}'.format(testState.s))

        # state 2s

        statePropt = {'P': 30, 's': testState.s}
        testState = StatePure(**statePropt)
        testState = fullyDefine_StatePure(testState, water_mpDF)

        expected_h = 2276.8
        expected_x = 0.847

        self.assertTrue(isWithin(testState.h, 3, '%', expected_h))
        print('Expected: {0}'.format(expected_h))
        print('Received: {0}'.format(testState.h))

        self.assertTrue(isWithin(testState.x, 3, '%', expected_x))
        print('Expected: {0}'.format(expected_x))
        print('Received: {0}'.format(testState.x))

    def test_subcLiq_01(self):
        # From MECH2201 - A9 Q1 - state 6

        state5 = StatePure(P=10, x=0)
        state5 = fullyDefine_StatePure(state5, water_mpDF)

        state6s = StatePure(P=10000, s=state5.s)
        state6s = fullyDefine_StatePure(state6s, water_mpDF)

        eta_p = 0.95

        W_is = state5.mu * (state6s.P - state5.P)
        W_ia = W_is / eta_p

        h6a = state5.h + W_ia
        self.assertTrue(isWithin(h6a, 3, '%', 202.45))

    def test_subcLiq_02(self):
        # From MECH2201 - A9 Q2 - state 6

        state5 = StatePure(P=5, x=0)
        state5 = fullyDefine_StatePure(state5, water_mpDF)

        state6s = StatePure(P=200, s=state5.s)
        state6s = fullyDefine_StatePure(state6s, water_mpDF)

        h6_manual = state5.h + state5.mu * (state6s.P - state5.P)

        self.assertTrue(isWithin(h6_manual, 3, '%', 138))

    def test_subcLiq_03(self):
        # From MECH2201 - A9 Q3 - state 4

        s3 = fullyDefine_StatePure(StatePure(P=6, x=0), water_mpDF)
        s4 = fullyDefine_StatePure(StatePure(P=150, s=s3.s), water_mpDF)

        s4_h_alt = 151.67  # manua calculation with vdp
        self.assertTrue(isWithin(s4.h, 3, '%', s4_h_alt))

        s5 = fullyDefine_StatePure(StatePure(P=150, x=0), water_mpDF)
        s6 = fullyDefine_StatePure(StatePure(P=12000, s=s5.s), water_mpDF)

        s6_h_alt = 479.59
        self.assertTrue(isWithin(s6.h, 3, '%', s6_h_alt))


class TestStateDefineMethods_R134a(unittest.TestCase):

    def CompareResults(self, testState: StatePure, expected: Dict, ptolerance: Union[float, int]):
        print('\n')
        for parameter in expected:
            assert hasattr(testState, parameter)
            self.assertTrue(isWithin(getattr(testState, parameter), ptolerance, '%', expected[parameter]))
            print('Expected: {0}'.format(expected[parameter]))
            print('Received: {0}'.format(getattr(testState, parameter)))

    def test_satVap_01(self):
        # From MECH3201 - Past Exam Q

        s1 = fullyDefine_StatePure(StatePure(P=200, x=1), R134a_mpDF)

        s7 = fullyDefine_StatePure(StatePure(P=450, x=0), R134a_mpDF)

        s8 = fullyDefine_StatePure(StatePure(P=200, h=s7.h), R134a_mpDF)

        s5 = fullyDefine_StatePure(StatePure(P=1200, x=0), R134a_mpDF)

        sM = fullyDefine_StatePure(StatePure(P=450, h=s5.h), R134a_mpDF)

        s3 = fullyDefine_StatePure(StatePure(P=450, x=1), R134a_mpDF)

        self.CompareResults(s1, {'h': 244.5, 's': 0.93788}, 3)
        self.CompareResults(s7, {'h': 68.8}, 3)
        self.CompareResults(s5, {'h': 117.79}, 3)
        self.CompareResults(sM, {'x': 0.26}, 3)
        self.CompareResults(s3, {'h': 257.58}, 3)

        s2s = fullyDefine_StatePure(StatePure(P=450, s=s1.s), R134a_mpDF)
        self.CompareResults(s2s, {'h': 261.09}, 3)

        s9 = fullyDefine_StatePure(StatePure(P=450, h=263.18), R134a_mpDF)
        self.CompareResults(s9, {'s': 0.9454}, 3)

        s4s = fullyDefine_StatePure(StatePure(s=s9.s, P=1200), R134a_mpDF)
        self.CompareResults(s4s, {'h': 284.38}, 3)

