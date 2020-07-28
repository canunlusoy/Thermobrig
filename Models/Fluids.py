from pandas import DataFrame

from Methods.ThprOps import fullyDefine_StatePure, define_StateIGas
from Models.States import StatePure

class Fluid:

    def __init__(self, mpDF: DataFrame):

        self.mpDF = mpDF
        self.defFcn = fullyDefine_StatePure

    def define(self, state: StatePure):
        """Wrapper around the state definition function to directly include the fluid's mpDF."""
        return self.defFcn(state, self.mpDF)

class IdealGas(Fluid):

    def __init__(self, mpDF: DataFrame, R: float):

        super(IdealGas, self).__init__(mpDF)
        self.defFcn = define_StateIGas
        self.R = R

        assert 'P' not in mpDF.mp.availableProperties  # for an ideal gas, P is independent of others


