from pandas import DataFrame

from typing import Union, List

from Methods.ThprOps import fullyDefine_StatePure, define_StateIGas
from Models.States import StatePure
from Utilities.Exceptions import NeedsExtrapolationError

class Fluid:

    def __init__(self, mpDF: DataFrame):

        self.mpDF = mpDF
        self.defFcn = fullyDefine_StatePure

        self.k = float('nan')
        self.cp = float('nan')

    def define(self, state: StatePure):
        """Wrapper around the state definition function to directly include the fluid's mpDF."""
        return self.defFcn(state, self.mpDF)

    def defineState_ifDefinable(self, state: StatePure):
        if not state.isFullyDefined() and state.isFullyDefinable():
            try:
                state.copy_fromState(self.define(state))
            except NeedsExtrapolationError:
                print('Fluid.defineState_ifDefinable: Leaving state @ {0} not fully defined'.format(state))
        return state


class IdealGas(Fluid):

    def __init__(self, mpDF: DataFrame, R: float, k: float = float('nan')):

        super(IdealGas, self).__init__(mpDF)
        self.defFcn = define_StateIGas
        self.R = R
        self.k = k

        assert 'P' not in mpDF.mp.availableProperties  # for an ideal gas, P is independent of others


