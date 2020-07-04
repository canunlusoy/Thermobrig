from pandas import DataFrame

from collections import namedtuple

import Utilities.DataOps
import Utilities.FileOps
import Utilities.Numeric
from Properties.States import StatePure

dataFile_path = r'D:\Belgeler\İşler\Thermobrig\Thermodynamic Property Data\Cengel_Formatted_Unified.xlsx'
dataFile_worksheet = 'WaterUnified'
dataFile = Utilities.FileOps.read_Excel_DF(dataFile_path, worksheet=dataFile_worksheet, headerRow=1, skipRows=[0])
MaterialPropertyDF = Utilities.DataOps.process_MaterialPropertyDF(dataFile)



# flowState a namedtuple instead of a dict - fields immutable and always the same
state_pure_properties_regular = ['P', 'T', 'h', 'u', 's']
state_pure_properties_mixture = ['x']
state_pure_properties = state_pure_properties_mixture + state_pure_properties_regular

state_pure = namedtuple('flowState_pure', state_pure_properties, defaults=[float('nan')] * len(state_pure_properties))

class State_Pure(namedtuple('flowState_pure', state_pure_properties, defaults=[float('nan')] * len(state_pure_properties))):

    def hasDefined(self, propertyName: str) -> bool:
        '''Returns true if a value for the given property is defined.'''
        if Utilities.Numeric.isNumeric(getattr(self, propertyName)):
            return True
        return False


def state_pure_isDefinable(flowState: StatePure):

    definable = False

    saturated = (0 <= flowState.x <= 1)
    if saturated:
        if sum(1 for property_regular in state_pure_properties_regular if Utilities.Numeric.isNumeric(getattr(flowState, property_regular))) >= 1:
            # if saturated mixture, values of quality & 1 other intensive property are enough to fully define state
            definable = True
    else:
        if sum(1 for property_regular in state_pure_properties_regular if Utilities.Numeric.isNumeric(getattr(flowState, property_regular))) >= 2:
            # if not a saturated mixture, values of 2 intensive properties (other than quality) are necessary to define state
            definable = True

    return definable


def state_pure_fullyDefine(flowState: StatePure, materialPropertyDF: DataFrame):

    assert state_pure_isDefinable(flowState)

    availableProperties = flowState.get_definedProperties()
    saturated = (0 <= flowState.x <= 1)

    if saturated and any(propertyName in availableProperties for propertyName in ['P', 'T']):
        if 'P' in availableProperties:
            pass


    else:
        # material is not in a saturated mixture state

        (refProp1_name, refProp1_value), (refProp2_name, refProp2_value) = availableProperties[:2]  # first 2 properties taken as reference properties - will use to find values of others
        (refProp1_min, refProp1_max) = Utilities.Numeric.get_rangeEndpoints(refProp1_value, 2)
        (refProp2_min, refProp2_max) = Utilities.Numeric.get_rangeEndpoints(refProp2_value, 2)

        queryTerm = '@refProp1_min <= {0} <= @refProp1_max and @refProp2_min <= {1} <= @refProp2_max'.format(refProp1_name, refProp2_name)
        matchingStates = MaterialPropertyDF.query(queryTerm)

    return matchingStates


statePropt = {'T':500, 'P':500}
testState = StatePure(**{'T':500, 'x':0.5})
state = state_pure_fullyDefine(testState, MaterialPropertyDF)
pass
