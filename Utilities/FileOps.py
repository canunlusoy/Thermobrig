from pandas import read_excel
from typing import Union, List


def read_Excel_DF(filepath: str, worksheet: Union[str, int] = None, indexColumn: int = None, headerRow: int = None, skipRows: List = None, squeeze: bool = False):
    '''Wrapper around pandas' read_excel for convenience of use. indexColumn, headerRow, skipRows are zero indexed.
    If **squeeze** and data is a single column, returns a series instead of a DataFrame.'''

    kwargs = {'sheet_name': worksheet,
              'index_cols:': indexColumn,
              'header': headerRow,
              'skipRows': skipRows,
              'squeeze': squeeze}

    return read_excel(filepath, **kwargs)


