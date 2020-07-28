
from typing import Dict

from Models.States import StatePure
from Methods.ThprOps import get_state_out_actual

from Utilities.Numeric import isNumeric, isWithin


class Device:

    def __init__(self):

        self.state_in: StatePure = None
        self.state_out: StatePure = None

    def set_states(self, state_in: StatePure = None, state_out: StatePure = None):
        if state_in is not None:
            self.state_in = state_in
        if state_out is not None:
            self.state_out = state_out

    def isFullyDefined(self):
        return self.state_in.isFullyDefined() and self.state_out.isFullyDefined()

    def apply_verify_relations(self):
        pass

    def set_or_verify(self, setDict: Dict):
        for parameterName in setDict:
            if hasattr(self, parameterName):
                if not isNumeric(getattr(self, parameterName)):
                    setattr(self, parameterName, setDict[parameterName])
                else:
                    assert isWithin(getattr(self, parameterName), 3, '%', setDict[parameterName])

class WorkDevice(Device):

    def __init__(self, eta_isentropic: float = 1, state_out_ideal: StatePure = None):
        super(WorkDevice, self).__init__()

        self.eta_isentropic = eta_isentropic

        if state_out_ideal is None:
            self.state_out_ideal = self.state_out
        else:
            self.state_out_ideal = state_out_ideal


    def get_workProvided(self):
        return self.state_out.h - self.state_in.h

    def get_workExtracted(self):
        return self.state_in.h - self.state_out.h

    def apply_verify_relations(self):
        super(WorkDevice, self).apply_verify_relations()





class Compressor(WorkDevice):
    def __init__(self, eta_isentropic: float = 1, state_out_ideal: StatePure = None):
        super(Compressor, self).__init__(eta_isentropic, state_out_ideal)


class Pump(WorkDevice):
    def __init__(self, eta_isentropic: float = 1, state_out_ideal: StatePure = None):
        super(Pump, self).__init__(eta_isentropic, state_out_ideal)


class Turbine(WorkDevice):
    def __init__(self, eta_isentropic: float = 1, state_out_ideal: StatePure = None):
        super(Turbine, self).__init__(eta_isentropic, state_out_ideal)


class HeatDevice(Device):
    def __init__(self, T_exit_fixed: float = float('nan'),
                 infer_constant_operatingP: bool = True, infer_fixed_exitT: bool = True):
        super(HeatDevice, self).__init__()

        self.infer_constant_operatingP = infer_constant_operatingP
        self.infer_fixed_exitT = infer_fixed_exitT

        self.T_exit_fixed = T_exit_fixed
        self.P_operating = float('nan')


    def get_heatProvided(self):
        return self.state_out.h - self.state_in.h

    def get_heatExtracted(self):
        return self.state_in.h - self.state_out.h


class Combustor(HeatDevice):
    def __init__(self):
        super(Combustor, self).__init__()


class Boiler(HeatDevice):
    def __init__(self, *args, **kwargs):
        super(Boiler, self).__init__(*args, **kwargs)
    # def __init__(self, T_exit_fixed: float = None,
    #              infer_constant_operatingP: bool = True,
    #              infer_fixed_exitT: bool = True):
    #
    #     super(Boiler, self).__init__(T_exit_fixed, infer_constant_operatingP, infer_fixed_exitT)




class Condenser(HeatDevice):
    def __init__(self):
        super(Condenser, self).__init__()

