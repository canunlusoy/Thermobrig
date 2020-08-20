import numpy as np

from collections import UserList
from typing import List, Iterable, Callable
from copy import deepcopy

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

    def __init__(self, LHS: List, RHS: float):

        self.source = None

        self._RHS_original = RHS
        self._LHS_original = LHS

        self.LHS = []
        self.RHS = RHS

        self.organizeTerms_fromOriginal()

    def organizeTerms_fromOriginal(self):
        """Iterates over the LHS terms provided in the **original equation description**, replaces variables with their values if they are known, moves constants to the RHS."""
        self.LHS = []

        for term in self._LHS_original:  # each term is a tuple
            constantFactors = []
            unknownFactors = []

            for item in term:  # items within the term are to be multiplied

                if item == (-1):
                    print(5)

                if isinstance(item, tuple):
                    # item is an object.attribute address, in form (object, 'attribute')
                    assert isinstance(item[1], str)

                    attribute = getattr_fromAddress(*item)
                    if isNumeric(attribute):
                        # If the object.attribute has a value, add it to constant factors
                        constantFactors.append(attribute)
                    else:
                        # If the object.attribute does not have a value, it is an unknownFactor
                        assert item not in unknownFactors, 'LinearEquationError: Same unknown appears twice in one term, i.e. a higher power of the unknown encountered - not a linear equation!'
                        unknownFactors.append(item)

                elif any(isinstance(item, _type) for _type in [float, int]):
                    # item is a number, i.e. a coefficient
                    assert isNumeric(item)
                    constantFactors.append(item)

            constantFactor = 1
            for factor in constantFactors:
                constantFactor *= factor

            if len(unknownFactors) != 0:
                # term has an unknown, e.g. term is in form of "6*x"
                self.LHS.append([constantFactor, unknownFactors])
            else:
                # term does not have an unknown, e.g. term is in form "6"
                self.RHS -= constantFactor  # move constant term to the RHS

        self._gatherUnknowns()

    def _gatherUnknowns(self):
        # GATHER UNKNOWNS APPEARING MULTIPLE TIMES - merge appearances, combine coefficients
        unknown_termIndices_inEquation = {}
        for termIndex, term in enumerate(self.LHS):
            unknowns = term[1]
            unknowns_key = tuple(unknowns)
            if unknowns_key not in unknown_termIndices_inEquation:
                unknown_termIndices_inEquation[unknowns_key] = [termIndex]
            else:
                unknown_termIndices_inEquation[unknowns_key].append(termIndex)

        for unknowns_key, termIndices_inEquation in unknown_termIndices_inEquation.items():
            if len(termIndices_inEquation) > 1:
                # unknown(s) appears multiple times in equation LHS, e.g. 6*x + 2*x + -3*x = 0 or e.g. 5*x*y + -2*x*y = 0

                # This unknown initially appears at term with index termIndices_inEquation[0] on the LHS of equation
                unknown_otherAppearances = [self.LHS[position] for position in termIndices_inEquation[1:]]
                unknown_coefficients_inOtherAppearances = [term[0] for term in unknown_otherAppearances]

                # Modify coefficient of initial appearance - move coefficients from other appearances
                for unknownCoefficient in unknown_coefficients_inOtherAppearances:
                    self.LHS[termIndices_inEquation[0]][0] += unknownCoefficient

                # Remove the subsequent appearances of the unknown since their coefficients have been moved to the initial appearance
                for termIndex in termIndices_inEquation[1:]:
                    self.LHS.pop(termIndex)

    def update(self):
        """Iterates over the unknown items in each term, checks if they have become numeric, i.e. have a value now whereas they previously didn't. If so, updates the constant factor
        by multiplying it with the newly determined value and removes it from the unknowns."""

        for termIndex, [term_constantFactor, term_unknowns_attributeAddresses] in enumerate(self.LHS):

            originalterm = deepcopy(self.LHS[termIndex])

            for attributeAddress in term_unknowns_attributeAddresses:
                attribute = getattr_fromAddress(*attributeAddress)
                if isNumeric(attribute):
                    # object.attribute which had previously been identified as unknown now has a value, add it to the constant factor product and remove from the unknowns
                    self.LHS[termIndex][0] *= attribute  # multiply it with the constant factor product
                    self.LHS[termIndex][1].remove(attributeAddress)  # remove it from the unknowns list

            if self.LHS[termIndex][1] == []:
                # if term has no unknowns, it is a constant, move to RHS
                self.RHS -= self.LHS[termIndex][0]
                self.LHS.pop(termIndex)

        self._gatherUnknowns()

    def get_unknowns(self):
        unknowns = []
        for [term_constantFactor, term_unknowns_attributeAddresses] in self.LHS:
            assert len(term_unknowns_attributeAddresses) > 0
            unknowns.append(term_unknowns_attributeAddresses)
        return unknowns

    def isSolvable(self):
        if number_ofUnknowns := len(self.get_unknowns()) == 1:
            return True
        return False

    def solve(self):
        print('\n')
        print(self._LHS_original)
        print(self.LHS)

        assert self.isSolvable()
        assert len(self.LHS) == 1  # all other constant terms must have been moved to the RHS
        return {self.LHS[0][1][0]: self.RHS / self.LHS[0][0]}  # attributeAddress: result - divide RHS by unknown's coefficient

    def solve_and_set(self):
        solution = self.solve()
        unknownAddress = list(solution.keys())[0]
        setattr_fromAddress(object=unknownAddress[0], address=unknownAddress[1], value=solution[unknownAddress])

    def __str__(self):
        termStrings = []
        for term in self.LHS:
            coefficient = term[0]
            unknownSet = term[1]

            termString = str(coefficient) + ' * '
            unknownStrings = []
            for unknown in unknownSet:
                unknownString = unknown[0].__class__.__name__ + '@' + str(id(unknown[0])) + '.' + unknown[1]
                unknownStrings.append(unknownString)
            termString += str.join(' * ', unknownStrings)
            termStrings.append(termString)

        termStrings = str.join(' + ', termStrings)
        return termStrings + ' = ' + str(self.RHS)

    def get_asDict(self):
        dictRepresentation = {}
        for [term_constantFactor, term_unknowns_attributeAddresses] in self.LHS:
            term_unknowns_attributeAddresses_key = tuple(term_unknowns_attributeAddresses)
            assert term_unknowns_attributeAddresses_key not in dictRepresentation, 'PrgError: Same unknowns encountered multiple times in the equation LHS, unknowns must have been gathered by now. (i.e. coefficients must have been combined as a single coefficient for the variable)'
            dictRepresentation[term_unknowns_attributeAddresses_key] = term_constantFactor

        dictRepresentation['RHS'] = self.RHS
        return dictRepresentation


class System_ofLinearEquations:

    def __init__(self, equations: List[LinearEquation]):
        self.equations = equations

    @staticmethod
    def isSolvable(equations: List[LinearEquation]):
        sampleEquation = equations[0]
        # Check if (# of equations) == (# of variables in sampleEquation)
        # Check if all equations have the same number of variables
        if len(equations) == len(sampleEquation.get_unknowns()):
            if all(equation.get_unknowns() == sampleEquation.get_unknowns() for equation in equations if equation is not sampleEquation):
                runningBoolean = True
                # Check if each unknown term has 1 unknown only, i.e. not a product of multiple unknowns, e.g. not 6*x*y but only 6*x.
                for equation in equations:
                    for termUnknowns in equation.get_unknowns():  # get_unknowns() returns the list of multiplied unknowns in each term.
                        if len(termUnknowns) != 1:
                            runningBoolean = False
                return runningBoolean
        return False

    def solve(self):

        unknowns = self.equations[0].get_unknowns()
        coefficients, constants = [], []

        for equation in self.equations:
            print('\n')
            print(equation._LHS_original)
            print(equation)

            equation_dict = equation.get_asDict()
            coefficients.append([equation_dict[tuple(unknown)] for unknown in unknowns])
            constants.append(equation_dict['RHS'])

        solution = np.linalg.solve(a=np.array(coefficients), b=np.array(constants))
        return {unknown[0]: float(solution[unknownIndex]) for unknownIndex, unknown in enumerate(unknowns)}  # unknown[0] since list of multiplied unknowns has only one unknown. Retrieve the unknown from the list

    def solve_and_set(self):
        solution = self.solve()
        for attributeAddress in solution:
            setattr_fromAddress(object=attributeAddress[0], address=attributeAddress[1], value=solution[attributeAddress])
