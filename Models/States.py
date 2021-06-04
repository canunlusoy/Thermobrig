from pandas import DataFrame

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Union, Dict, List

from Utilities.Numeric import isNumeric, isWithin


@dataclass  # TODO: Not hashing as intended. Instances with identical content have same hash.
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

    def __hash__(self):
        # In previous versions, we had unsafe_hash = True in dataclass decorator. This generated a __hash__ method based on the __eq__ method.
        # Two equal but non-identical states therefore had the same hash, and therefore caused problems in dictionary keys, observed in LinearEquations.
        # This overwritten __hash__ method returns a hash based on IDENTITY, not value/contents (__eq__).
        return hash(id(self))

    def hasDefined(self, propertyName: Union[str, List]) -> bool:
        """Returns true if a value for the given property is defined."""
        if isinstance(propertyName, str):
            return isNumeric(getattr(self, propertyName))
        elif isinstance(propertyName, list):
            return all(isNumeric(getattr(self, property)) for property in propertyName)

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
        """Returns OrderedDict mapping property names to values for properties which have numeric values defined. Properties are ordered according to preference in interpolation."""
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
            print('Initialized state ' + str(self) + ' from DFRow, properties ' + str(missingProperties_inDFRow) + ' not provided in DataFrame row.')
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
        return self

    def clearFields(self, clearFields: List[str] = None, keepFields: List[str] = None):
        if keepFields is None and clearFields is not None:
            for field in clearFields:
                assert hasattr(self, field)
                setattr(self, field, float('nan'))
        elif clearFields is None and keepFields is not None:
            for field in self._properties_all:
                if field not in keepFields:
                    setattr(self, field, float('nan'))
        else:
            pass

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

    def set_or_verify(self, setDict: Dict, percentDifference: float = 3):
        for parameterName in setDict:
            if parameterName in self._properties_all:
                if not self.hasDefined(parameterName):
                    self.set({parameterName: setDict[parameterName]})
                else:
                    assert isWithin(getattr(self, parameterName), percentDifference, '%', setDict[parameterName])


class StateIGas(StatePure):

    # In addition to properties of StatePure

    # Properties for variable-c analysis
    s0: float = float('nan')
    P_r: float = float('nan')
    mu_r: float = float('nan')

    x: int = 2  # superheated vapor / gas

    _properties_regular = ['T', 'P', 'mu', 'h', 'u']  # ordered in preference to use in interpolation
    _properties_variable_c = ['P_r', 'mu_r', 's0']  # T-dependent properties used in analysis with variable specific heats
    _properties_all = _properties_regular + _properties_variable_c

    _properties_Tdependent = ['T', 'P_r', 'mu_r', 'h', 'u', 's0']

    def __repr__(self):
        return 'StateIGas(P:{0}, T:{1}, mu:{2}, h:{3}, u:{4}, P_r:{5}, mu_r:{6}, s0:{7})'.format(self.P, self.T, self.mu, self.h, self.u, self.P_r, self.mu_r, self.s0)

    def isFullyDefined(self, constant_c: bool = True, consider_mixProperties: bool = True) -> bool:
        propertyList = self._properties_regular
        if not constant_c:  # if constant c analysis is made, does not care if the variable-c analysis parameters are defined or not
            propertyList = self._properties_all
        if all(self.hasDefined(propertyName) for propertyName in propertyList):
            return True
        return False

    def isFullyDefinable(self):
        """Checks if all state variables can be determined based on the availability of properties in the ideal gas law, P*mu = R*T. \n
        R (gas constant) is a Fluid property, and is not carried with the StateIGas object. However, in use, Fluid should be defined when StateIGas is used. So assumes R is known."""

        definable = False

        # Ideal gas law: P * mu = R * T
        #                _ * __ = R * _

        if self.hasDefined(['P', 'mu']):
            # if P & mu defined (both LHS terms), T can be found, assuming R is known
            definable = True
        elif any(self.hasDefined(property) for property in self._properties_Tdependent) and any(self.hasDefined(property) for property in ['P', 'mu']):
            # if T is defined, and one of P or mu is defined, the other unknown LHS term can be found, assuming R is known
            definable = True
        elif self.hasDefined('T'):  # TODO: Temp. StateIGas left undefined because this method returns False, even when T-dependent tabulated properties can be found.
            definable = True

        # An alternative method to check if isFullyDefinable is to check if number of unknowns among P, T, mu is 1. This method here is more descriptive so leaving as is.
        return definable

class FlowPoint_Pure(StatePure):

    def __init__(self, baseState: StatePure, flow: 'Flow'):
        """Class for flow-aware states. Normally, states are unaware / independent of flows and are simply data containers for thermodynamic information. Flow points represent **points in flows**,
        and hence allow access to flow data through the reference to the flow, and contain the state information inherently, in the same way as a state object."""

        self.baseState = baseState
        self.flow = flow

    # Custom __eq__ method - the default version does not take flow of state into account. Overriding __eq__ could have been avoided by simpler use of dataclass but due to property (getter/setter) based
    # nature of this dataclass, I used this method.

    def __members(self):
        return (self.baseState, self.flow)

    def __eq__(self, other):
        if isinstance(other, StatePure):
            return all(getattr(self, property) == getattr(other, property) for property in self._properties_all) and (self.flow is other.flow)
        else:
            return False

    def __hash__(self):  # if __eq__ is overridden, __hash__ also needs to be overridden.
        return hash(self.__members())

    #

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

    def set(self, setDict: Dict):
        """Sets values of the properties to the values provided in the dictionary."""
        
        for parameterName in setDict:
            if parameterName in self._properties_all:
                setattr(self, parameterName, setDict[parameterName])


class FlowPoint_IGas(StateIGas):

    def __init__(self, baseState: StateIGas, flow: 'Flow'):
        """Class for flow-aware states. Normally, states are unaware / independent of flows and are simply data containers for thermodynamic information. Flow points represent **points in flows**,
        and hence allow access to flow data through the reference to the flow, and contain the state information inherently, in the same way as a state object."""

        self.baseState = baseState
        self.flow = flow

    # Custom __eq__ method - the default version does not take flow of state into account. Overriding __eq__ could have been avoided by simpler use of dataclass but due to property (getter/setter) based
    # nature of this dataclass, I used this method.

    def __members(self):
        return (self.baseState, self.flow)

    def __eq__(self, other):
        if isinstance(other, StatePure):
            return all(getattr(self, property) == getattr(other, property) for property in self._properties_all) and (self.flow is other.flow)
        else:
            return False

    def __hash__(self):  # if __eq__ is overridden, __hash__ also needs to be overridden.
        return hash(self.__members())

    #

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

    def get_P_r(self):
        return getattr(self.baseState, 'P_r')

    def set_P_r(self, value):
        setattr(self.baseState, 'P_r', value)

    P_r = property(fget=get_P_r, fset=set_P_r)

    def get_mu_r(self):
        return getattr(self.baseState, 'mu_r')

    def set_mu_r(self, value):
        setattr(self.baseState, 'mu_r', value)

    mu_r = property(fget=get_mu_r, fset=set_mu_r)

    def set(self, setDict: Dict):
        """Sets values of the properties to the values provided in the dictionary."""

        for parameterName in setDict:
            if parameterName in self._properties_all:
                setattr(self, parameterName, setDict[parameterName])