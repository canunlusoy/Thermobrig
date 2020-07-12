from pandas import DataFrame

from collections import OrderedDict
from dataclasses import dataclass
from typing import Union, Dict, List

from Utilities.Numeric import isNumeric, get_rangeEndpoints

@dataclass
class StatePure:
    P: float = float('nan')
    T: float = float('nan')
    mu: float = float('nan')
    h: float = float('nan')
    u: float = float('nan')
    s: float = float('nan')
    x: float = float('nan')

    properties_regular = ['P', 'T', 'mu', 'h', 'u', 's']  # ordered in preference to use in interpolation
    properties_mixture = ['x']
    properties_all = properties_regular + properties_mixture

    def hasDefined(self, propertyName: str) -> bool:
        """Returns true if a value for the given property is defined."""
        if isNumeric(getattr(self, propertyName)):
            return True
        return False

    def isFullyDefined(self, consider_mixProperties: bool = True) -> bool:
        propertyList = self.properties_all
        if not consider_mixProperties:
            propertyList = self.properties_regular
        if all(self.hasDefined(propertyName) for propertyName in propertyList):
            return True
        return False

    def isFullyDefinable(self):
        definable = False
        saturated = (0 <= self.x <= 1)

        if saturated:
            if sum(1 for property_regular in self.properties_regular if isNumeric(getattr(self, property_regular))) >= 1:
                # if saturated mixture, values of quality & 1 other intensive property are enough to fully define state
                definable = True
        else:
            if sum(1 for property_regular in self.properties_regular if isNumeric(getattr(self, property_regular))) >= 2:
                # if not a saturated mixture, values of 2 intensive properties (other than quality) are necessary to define state
                definable = True

        return definable


    def get_asDict_definedProperties(self) -> OrderedDict:
        """Returns OrderedDict mapping property names to values for properties which have numeric values defined. ThermalProperties are ordered according to preference in interpolation."""
        return OrderedDict([(propertyName, getattr(self, propertyName)) for propertyName in self.properties_all if self.hasDefined(propertyName)])

    def get_asList_definedPropertiesNames(self) -> List:
        """Returns list of property names whose values are numeric, i.e. whose values are defined."""
        return [propertyName for propertyName in self.properties_all if self.hasDefined(propertyName)]

    def get_asDict_allProperties(self, ordered: bool = False) -> Union[Dict, OrderedDict]:
        dictClass = dict
        if ordered:
            dictClass = OrderedDict
        return dictClass([(propertyName, getattr(self, propertyName)) for propertyName in self.properties_all])

    def init_fromDFRow(self, dfRow: DataFrame):
        """Sets property attributes of the StatePure using columns of the provided DataFrame row. Assumes only a single row is provided."""
        assert len(dfRow.index) == 1
        dfRow = dfRow.squeeze()
        missingProperties_inDFRow = []
        for propertyName in self.properties_all:
            if propertyName in dfRow.index:
                setattr(self, propertyName, float(dfRow[propertyName]))
            else:
                missingProperties_inDFRow.append(propertyName)
        if missingProperties_inDFRow != []:
            print('ThermalProperties ' + str(missingProperties_inDFRow) + ' not provided in DataFrame row.')
        return self

    def init_fromDict(self, dictionary: Dict):
        """Sets property attributes of the StatePure using values provided in the dictionary."""
        for propertyName in dictionary.keys():
            if propertyName in self.properties_all:
                setattr(self, propertyName, dictionary[propertyName])
        return self

    def init_fromState(self, state: 'StatePure'):
        for propertyName in self.properties_all:
            setattr(self, propertyName, getattr(state, propertyName))



