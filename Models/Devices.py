
from typing import Dict, List

from Models.States import StatePure
from Methods.ThprOps import get_state_out_actual

from Utilities.Numeric import isNumeric, isWithin, twoList


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


    @property
    def workProvided(self):
        return self.state_out.h - self.state_in.h

    @property
    def workExtracted(self):
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
                 infer_constant_lineP: bool = True, infer_fixed_exitT: bool = True):
        super(HeatDevice, self).__init__()

        self._infer_constant_linePressures = infer_constant_lineP
        self.lines: List[twoList[StatePure]] = []
        self.linePressures = {}
        # assumes pressure remains constant in each line passing through device, e.g. if a boiler is used twice by the same flow, each time, the pressure of the line
        # passing through the boiler will be different but the pressure inside the line will be constant - effectively, sets the inlet and outlet states of each line
        # passing through boiler to have the same pressure.

        self._infer_fixed_exitT = infer_fixed_exitT
        self.T_exit_fixed = T_exit_fixed
        # assumes each line passing through the boiler reaches the same exit temperature. Once an exit temperature is available, sets T_exit_fixed.

    def set_states(self, state_in: StatePure = None, state_out: StatePure = None):
        if (line_endStates := twoList([state_in, state_out])) not in self.lines:
            self.lines.append(line_endStates)
            # Set state_in, state_out as the currently set pair - but ideally, when making use of endStates of HeatDevices, methods must make provisions for lines
            self.state_in = state_in
            self.state_out = state_out

    def infer_constant_linePressures(self):
        for line_endStates in self.lines:
            number_ofNumericPvals = sum(1 for state in line_endStates if isNumeric(getattr(state, 'P')))
            if number_ofNumericPvals == 2:
                assert isWithin(line_endStates[0].P, 3, '%', line_endStates[1].P)
            elif number_ofNumericPvals == 1:
                state_withNonNumericPval = line_endStates.itemSatisfying(lambda state: not isNumeric(getattr(state, 'P')))
                state_withNumericPval = line_endStates.other(state_withNonNumericPval)
                state_withNonNumericPval.P = state_withNumericPval.P

    def infer_fixed_exitT(self):
        state_out_withNumericT = None
        for line_endStates in self.lines:
            if line_endStates[1].hasDefined('T'):
                state_out_withNumericT = line_endStates[1]
                break
        self.set_or_verify({'T_exit_fixed': state_out_withNumericT.T})
        for line_endStates in self.lines:
            line_endStates[1].set_or_verify({'T': self.T_exit_fixed})


    @property
    def heatProvided(self):
        return self.state_out.h - self.state_in.h

    @property
    def heatExtracted(self):
        return self.state_in.h - self.state_out.h


class Combustor(HeatDevice):
    def __init__(self):
        super(Combustor, self).__init__()


class Boiler(HeatDevice):
    def __init__(self, *args, **kwargs):
        super(Boiler, self).__init__(*args, **kwargs)


class Condenser(HeatDevice):
    def __init__(self):
        super(Condenser, self).__init__()

