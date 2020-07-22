from pandas import DataFrame


class Fluid:

    def __init__(self, mpDF: DataFrame, isIGas: bool = False):

        self.mpDF = mpDF
