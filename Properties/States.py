from pandas import DataFrame

from collections import OrderedDict
from dataclasses import dataclass
from typing import Union, Dict

import Utilities.Numeric


@dataclass
class StatePure:
    P: float = float('nan')
    T: float = float('nan')
    h: float = float('nan')
    u: float = float('nan')
    s: float = float('nan')
    x: float = float('nan')

    properties_regular = ['P', 'T', 'h', 'u', 's']  # ordered in preference to use in interpolation
    properties_mixture = ['x']
    properties_all = properties_regular + properties_mixture

    def hasDefined(self, propertyName: str) -> bool:
        """Returns true if a value for the given property is defined."""
        if Utilities.Numeric.isNumeric(getattr(self, propertyName)):
            return True
        return False

    def isFullyDefined(self, consider_mixProperties: bool = True) -> bool:
        propertyList = self.properties_all
        if not consider_mixProperties:
            propertyList = self.properties_regular
        if all(self.hasDefined(propertyName) for propertyName in propertyList):
            return True
        return False

    def get_definedProperties(self) -> OrderedDict:
        """Returns OrderedDict mapping property names to values for properties which have numeric values defined. Properties are ordered according to preference in interpolation."""
        return OrderedDict([(propertyName, getattr(self, propertyName)) for propertyName in self.properties_all if self.hasDefined(propertyName)])

    def get_allProperties(self, ordered: bool = False) -> Union[Dict, OrderedDict]:
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
            print('Properties ' + str(missingProperties_inDFRow) + ' not provided in DataFrame row.')