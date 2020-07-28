from pandas import DataFrame

from Methods.ThprOps import fullyDefine_StatePure, define_StateIGas

class Fluid:

    def __init__(self, mpDF: DataFrame):

        self.mpDF = mpDF
        self.defFcn = fullyDefine_StatePure


class IdealGas(Fluid):

    def __init__(self, mpDF: DataFrame, R: float):

        super(IdealGas, self).__init__(mpDF)
        self.defFcn = define_StateIGas
        self.R = R

        assert 'P' not in mpDF.mp.availableProperties  # for an ideal gas, P is independent of others


