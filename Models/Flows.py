
from typing import Union, List

from Models.Fluids import Fluid


class Flow:

    def __init__(self, workingFluid: Fluid):

        # Not considering flows with multiple fluids, one flow can contain only one fluid
        self.states = []
