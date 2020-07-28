from pandas import read_excel, DataFrame
from pandas.api.extensions import register_dataframe_accessor
from typing import Union, List, Dict

from Models.States import StatePure
from Utilities.Numeric import isNumeric


def read_Excel_DF(filepath: str, worksheet: Union[str, int] = None, indexColumn: int = None, headerRow: int = None, skipRows: List = None, squeeze: bool = False):
    '''Wrapper around pandas' read_excel for convenience of use. indexColumn, headerRow, skipRows are zero indexed.
    If **squeeze** and data is a single column, returns a series instead of a DataFrame.'''

    kwargs = {'sheet_name': worksheet,
              'index_cols:': indexColumn,
              'header': headerRow,
              'skipRows': skipRows,
              'squeeze': squeeze}

    return read_excel(filepath, **kwargs)


@register_dataframe_accessor('mp')
class MaterialPropertyAccessor:

    def __init__(self, mpDF: DataFrame):
        self._mpDF = mpDF
        self._determine_criticalPointProperties()

    def _determine_criticalPointProperties(self):
        # Assumes the saturated state with the maximum temperature is the critical point - users should provide many saturated states and ideally the critical point state in their data as well
        # This assumption will return very inaccurate critical point properties if users provide data of states significantly below critical point properties

        if 'x' in self.availableProperties:
            saturatedStates = self._mpDF.query('0 <= x <= 1')
            maximumTemperature = saturatedStates['T'].max()
            criticalPointCandidates = saturatedStates.query('T == {0}'.format(maximumTemperature))
            if not criticalPointCandidates.empty:
                self.criticalPoint = StatePure().init_fromDFRow(criticalPointCandidates.head(1))
            else:
                print('ThDataError: No state found when looking for the saturated state with the maximum temperature. Are there any saturated states provided in the data?')

    @property
    def availableProperties(self):
        return list(self._mpDF.columns)


@register_dataframe_accessor('cq')
class CustomQueryAccessor:

    def __init__(self, mpDF: DataFrame):
        self._mpDF = mpDF

    @property
    def suphVaps(self) -> DataFrame:
        """Returns superheated vapor states, identified by a quality of 2."""
        return self._mpDF.query('x == 2')

    @property
    def subcLiqs(self) -> DataFrame:
        """Returns subcooled liquid states, identified by a quality of -1."""
        return self._mpDF.query('x == -1')

    def cQuery(self, conditions: Dict) -> DataFrame:
        """Custom query method - wrapper around the regular DataFrame.query for convenience."""
        queryString_components = []

        for columnName, columnValue in conditions.items():
            if isinstance(columnValue, tuple):
                if all(isNumeric(value) for value in columnValue):
                    queryString_components.append('{0} <= {1} <= {2}'.format(columnValue[0], columnName, columnValue[1]))
                elif isinstance(sign:= columnValue[0], str) and isNumeric(columnValue[1]):
                    if any(sign == ltSign for ltSign in ['<', '<=', '>', '>=']):
                        queryString_components.append('{0} {1} {2}'.format(columnName, sign, columnValue[0]))
                    else:
                        raise AssertionError('Query string could not be resolved.')
            elif any(isinstance(columnValue, _type) for _type in [float, int]):
                queryString_components.append('{0} == {1}'.format(columnName, columnValue))

        queryString = str.join(' and ', queryString_components)
        return self._mpDF.query(queryString)



def process_MaterialPropertyDF(materialPropertyDF: DataFrame):
    # TODO
    return materialPropertyDF