from pandas import DataFrame

from typing import Dict


def build_queryString(conditions: Dict) -> str:
    """Constructs a query string for use in DataFrame.query method. Conditions are combined into a chain with "and" operators. Keys in the conditions dictionary should be column names,
    and values can be numbers or tuples of 2 numbers for intervals."""

    queryString_components = []

    for columnName, columnValue in conditions.items():
        if isinstance(columnValue, tuple):
            queryString_components.append('{0} <= {1} <= {2}'.format(columnValue[0], columnName, columnValue[1]))
        elif any(isinstance(columnValue, _type) for _type in [float, int]):
            queryString_components.append('{0} == {1}'.format(columnName, columnValue))

    queryString = str.join(' and ', queryString_components)
    return queryString
