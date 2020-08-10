import numpy as np

from collections import UserList
from typing import List, Iterable, Callable

from Utilities.Numeric import isNumeric


def findItem(items: Iterable, condition):
    """Returns the first item in the list of states satisfying the condition."""
    for item in items:
        if condition(item):
            return item


def getattr_fromAddress(object, address: str):
    address_split = address.split('.')
    for address_level in address_split:
        object = getattr(object, address_level)
    return object


def setattr_fromAddress(object, address: str, value):
    address_split = address.split('.')
    for address_level in address_split[:-1]:
        object = getattr(object, address_level)
    setattr(object, address_split[-1], value)


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

        self.variables_coefficients = {}
        self.constant = equation[1]  # equation[1] is the RHS
        self.source = None

        assert isNumeric(self.constant), 'Right hand side value (constant value) not numeric!'

        for term in equation[0]:  # equation[0] is the LHS
            # term: (coefficient * variable)

            numeric, nonNumeric = [], []
            for item in term:  # item is either coefficient or variable


                item_value = item

                if isinstance(item, tuple):
                    assert len(item) == 2 and isinstance(item[1], str)
                    item_value = getattr_fromAddress(item[0], item[1])

                if isNumeric(item_value):
                    numeric.append(item_value)
                else:
                    nonNumeric.append(item)

            if len(numeric) == 1 and len(nonNumeric) == 1:
                # if there is a numeric and a non-numeric item in the term, arranging them correctly would make a difference.
                coefficient = numeric[0]
                variable = nonNumeric[0]
            elif len(numeric) == 2:
                (coefficient, variable) = numeric
            else:
                # if not, doesn't make a difference
                (coefficient, variable) = term

            if len(numeric) == 2:
                # if a (coefficient * variable) term on the LHS is numeric, i.e. the variable value is known, the term is a constant, move it to RHS
                self.constant -= (coefficient * variable)
            else:
                self.variables_coefficients.update({variable: coefficient})

    @property
    def variables(self):
        return list(self.variables_coefficients.keys())

    @property
    def coefficients(self):
        return list(self.variables_coefficients.values())

    def isSolvable(self):
        """If an equation is solvable by itself, there should be one unknown."""
        # There is one unknown, and its coefficient is also known
        return len(self.variables) == 1 and all(isNumeric(coefficient) for coefficient in self.coefficients)

    def solve(self) -> List:
        """Solves the single variable linear equation and returns the value of the variable. Returns a list of [variable, solution], but does not readily set the variable's value."""
        assert self.isSolvable()
        return [self.variables[0], self.constant / list(self.variables_coefficients.values())[0]]

    def solve_andSet(self, returnSolution: bool = False):
        """Solves the single variable linear equation and sets the value of the variable to the solution."""
        solution = [variableAddress, value] = self.solve()
        setattr_fromAddress(variableAddress[0], variableAddress[1], solution)
        return solution


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
            coefficients.append([equation.variables_coefficients[variable] for variable in variables])
            constants.append(equation.constant)

        solution = np.linalg.solve(a=np.array(coefficients), b=np.array(constants))
        return {variable: solution[variableIndex] for variableIndex, variable in enumerate(variables)}


