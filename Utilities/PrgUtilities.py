import numpy as np

from collections import UserList
from typing import List, Iterable, Callable

from Utilities.Numeric import isNumeric


def findItem(items: Iterable, condition):
    """Returns the first item in the list of states satisfying the condition."""
    for item in items:
        if condition(item):
            return item


class twoList(UserList):

    def __init__(self, *args):
        super(twoList, self).__init__(*args)

    def other(self, otherThan):
        return self[self.index(otherThan) - 1]

    def itemSatisfying(self, condition: Callable):
        for item in self:
            if condition(item):
                return item
        return None


class LinearEquation:

    def __init__(self, equation: List):
        # [ [(coeff1, var1), (coeff2, var2), (coeff3, var3)], const ]

        self.coefficients = {}
        self.constant = equation[1]  # equation[1] is the RHS

        for (coefficient, variable) in equation[0]:  # equation[0] is the LHS
            if isNumeric(variable):
                self.constant -= (coefficient * variable)
            else:
                self.coefficients.update({variable: coefficient})

    @property
    def variables(self):
        return list(self.coefficients.keys())

    def isSolvable(self):
        """If an equation is solvable by itself, there should be one unknown."""
        return len(self.variables) == 1

    def solve(self) -> List:
        """Solves the single variable linear equation and returns the value of the variable. Returns a list of [variable, solution], but does not readily set the variable's value."""
        assert self.isSolvable()
        return [self.variables[0], self.constant / list(self.coefficients.values())[0]]


class System_ofLinearEquations:

    def __init__(self, equations: List[LinearEquation]):
        self.equations = equations

    @staticmethod
    def isSolvable(equations: List[LinearEquation]):
        sampleEquation = equations[0]
        # Check if (# of equations) == (# of variables in sampleEquation)
        # Check if all equations have the same number of variables
        if len(equations) == len(sampleEquation.variables) and all(len(equation.variables) == sampleEquation.variables for equation in equations if equation is not sampleEquation):
            return True
        return False

    def solve(self):
        variables = self.equations[0].variables

        coefficients, constants = [], []
        for equation in self.equations:
            coefficients.append([equation.coefficients[variable] for variable in variables])
            constants.append(equation.constant)

        solution = np.linalg.solve(a=np.array(coefficients), b=np.array(constants))
        return {variable: solution[variableIndex] for variableIndex, variable in enumerate(variables)}


