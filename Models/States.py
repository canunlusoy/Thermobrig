from pandas import DataFrame

from collections import OrderedDict
from dataclasses import dataclass
from typing import Union, Dict, List

from Utilities.Numeric import isNumeric, isWithin


@dataclass(unsafe_hash=True)
class StatePure:
    P: float = float('nan')
    T: float = float('nan')
    mu: float = float('nan')
    h: float = float('nan')
    u: float = float('nan')
    s: float = float('nan')
    x: float = float('nan')

    _properties_regular = ['P', 'T', 'mu', 'h', 'u', 's']  # ordered in preference to use in interpolation
    _properties_mixture = ['x']
    _properties_all = _properties_regular + _properties_mixture

    def hasDefined(self, propertyName: str) -> bool:
        """Returns true if a value for the given property is defined."""
        return isNumeric(getattr(self, propertyName))

    def isFullyDefined(self, consider_mixProperties: bool = True) -> bool:
        propertyList = self._properties_all
        if not consider_mixProperties:
            propertyList = self._properties_regular
        if all(self.hasDefined(propertyName) for propertyName in propertyList):
            return True
        return False

    def isFullyDefinable(self):
        definable = False
        saturated = (0 <= self.x <= 1)

        if saturated:
            if sum(1 for property_regular in self._properties_regular if isNumeric(getattr(self, property_regular))) >= 1:
                # if saturated mixture, values of quality & 1 other intensive property are enough to fully define state
                definable = True
        else:
            if sum(1 for property_regular in self._properties_regular if isNumeric(getattr(self, property_regular))) >= 2:
                # if not a saturated mixture, values of 2 intensive properties (other than quality) are necessary to define state
                definable = True

        return definable

    def get_asDict_definedProperties(self) -> OrderedDict:
        """Returns OrderedDict mapping property names to values for properties which have numeric values defined. Models are ordered according to preference in interpolation."""
        return OrderedDict([(propertyName, getattr(self, propertyName)) for propertyName in self._properties_all if self.hasDefined(propertyName)])

    def get_asList_definedPropertiesNames(self) -> List:
        """Returns list of property names whose values are numeric, i.e. whose values are defined."""
        return [propertyName for propertyName in self._properties_all if self.hasDefined(propertyName)]

    def get_asDict_allProperties(self, ordered: bool = False) -> Union[Dict, OrderedDict]:
        dictClass = dict
        if ordered:
            dictClass = OrderedDict
        return dictClass([(propertyName, getattr(self, propertyName)) for propertyName in self._properties_all])

    def init_fromDFRow(self, dfRow: DataFrame):
        """Sets property attributes of the StatePure using columns of the provided DataFrame row. Assumes only a single row is provided."""
        assert len(dfRow.index) == 1
        dfRow = dfRow.squeeze()
        missingProperties_inDFRow = []
        for propertyName in self._properties_all:
            if propertyName in dfRow.index:
                setattr(self, propertyName, float(dfRow[propertyName]))
            else:
                missingProperties_inDFRow.append(propertyName)
        if missingProperties_inDFRow != []:
            print('Models ' + str(missingProperties_inDFRow) + ' not provided in DataFrame row.')
        return self

    def init_fromDict(self, dictionary: Dict):
        """Sets property attributes of the StatePure using values provided in the dictionary."""
        for propertyName in dictionary.keys():
            if propertyName in self._properties_all:
                setattr(self, propertyName, dictionary[propertyName])
        return self

    def init_fromState(self, state: 'StatePure'):
        for propertyName in self._properties_all:
            setattr(self, propertyName, getattr(state, propertyName))

    def copy_fromState(self, referenceState: 'StatePure'):
        for propertyName in self._properties_all:
            if isNumeric(referenceValue := getattr(referenceState, propertyName)):
                setattr(self, propertyName, referenceValue)

    def copy_or_verify_fromState(self, referenceState: 'StatePure', pTolerance: float = 3):
        """Copies property values from the provided reference state. If property already has a value defined, compares it to the one desired to be assigned, raises error if values do not match.
        If the values match, still copies the value from the referenceState - decimals might change."""
        for propertyName in self._properties_all:
            if isNumeric(referenceValue := getattr(referenceState, propertyName)):
                if not isNumeric(getattr(self, propertyName)):
                    setattr(self, propertyName, referenceValue)
                else:
                    # property has a value defined
                    if not isWithin(getattr(self, propertyName), 3, '%', referenceValue):
                        raise AssertionError

    def set(self, setDict: Dict):
        """Sets values of the properties to the values provided in the dictionary."""
        for parameterName in setDict:
            if parameterName in self._properties_all:
                setattr(self, parameterName, setDict[parameterName])

    def set_or_verify(self, setDict: Dict):
        for parameterName in setDict:
            if parameterName in self._properties_all:
                if not self.hasDefined(parameterName):
                    setattr(self, parameterName, setDict[parameterName])
                else:
                    assert isWithin(getattr(self, parameterName), 3, '%', setDict[parameterName])


class StateIGas(StatePure):

    # In addition to properties of StatePure
    s0: float = float('nan')
    x: int = 2  # superheated vapor / gas

    _properties_regular = ['P', 'T', 'mu', 'h', 'u', 's0']  # ordered in preference to use in interpolation
    _properties_mixture = ['x']
    _properties_all = _properties_regular + _properties_mixture


class FlowPoint(StatePure):

    def __init__(self, baseState: StatePure, flow: 'Flow'):
        """Class for flow-aware states. Normally, states are unaware / independent of flows and are simply data containers for thermodynamic information. Flow points represent **points in flows**,
        and hence allow access to flow data through the reference to the flow, and contain the state information inherently, in the same way as a state object."""

        self.baseState = baseState
        self.flow = flow

    def get_P(self):
        return getattr(self.baseState, 'P')

    def set_P(self, value):
        setattr(self.baseState, 'P', value)

    P = property(fget=get_P, fset=set_P)

    def get_T(self):
        return getattr(self.baseState, 'T')

    def set_T(self, value):
        setattr(self.baseState, 'T', value)

    T = property(fget=get_T, fset=set_T)

    def get_h(self):
        return getattr(self.baseState, 'h')

    def set_h(self, value):
        setattr(self.baseState, 'h', value)

    h = property(fget=get_h, fset=set_h)

    def get_u(self):
        return getattr(self.baseState, 'u')

    def set_u(self, value):
        setattr(self.baseState, 'u', value)

    u = property(fget=get_u, fset=set_u)

    def get_mu(self):
        return getattr(self.baseState, 'mu')

    def set_mu(self, value):
        setattr(self.baseState, 'mu', value)

    mu = property(fget=get_mu, fset=set_mu)

    def get_s(self):
        return getattr(self.baseState, 's')

    def set_s(self, value):
        setattr(self.baseState, 's', value)

    s = property(fget=get_s, fset=set_s)

    def get_x(self):
        return getattr(self.baseState, 'x')

    def set_x(self, value):
        setattr(self.baseState, 'x', value)

    x = property(fget=get_x, fset=set_x)

    def get_s0(self):
        return getattr(self.baseState, 's0')

    def set_s0(self, value):
        setattr(self.baseState, 's0', value)

    s0 = property(fget=get_s0, fset=set_s0)
