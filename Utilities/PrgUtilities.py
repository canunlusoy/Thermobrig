import numpy as np

from collections import UserList
from typing import List, Iterable, Callable, Dict, Set
from itertools import combinations

from Utilities.Numeric import isNumeric

def findItem(items: Iterable, condition):
    """Returns the first item in the list of states satisfying the condition."""
    for item in items:
        if condition(item):
            return item


def getattr_fromAddress(object, address: str):
    address_split = address.split('.')
    for address_level in address_split:
        try:
            object = getattr(object, address_level)
        except AttributeError:
            print('getattr_fromAddress - ERROR: {0} does not have attribute {1}'.format(object, address_level))
    return object


def setattr_fromAddress(object, attributeName: str, value):
    address_split = attributeName.split('.')
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

        self._one = 1

        self.organizeTerms_fromOriginal()

    def organizeTerms_fromOriginal(self):
        """Iterates over the LHS terms provided in the **original equation description**, replaces variables with their values if they are known, moves constants to the RHS."""
        self.LHS = []

        # LHS: [  ]
        # LHS: [ term1, term2, term3 ]
        # LHS: [ (   ), (   ), (   ) ]
        # LHS: [ ( item1, item2, item3 ), term2, term3 ]
        #          _______________  _______________  __
        # LHS: [ ( (obj1, 'attr1'), (obj2, 'attr2'), 20 ), term2, term3 ]


        # Expand brackets
        def someTermsHaveListItems():
            for term in self._LHS_original:
                if any(isinstance(item, list) for item in term):
                    return True
            return False

        while someTermsHaveListItems():
            for termIndex, Term in enumerate(self._LHS_original):
                newTerms_toAdd = []
                listItems_inTerm = [item for item in Term if isinstance(item, list)]
                hasListItems = len(listItems_inTerm) > 0

                for listItem_inTerm in listItems_inTerm:
                    otherItems_inTerm = tuple(item for item in Term if item is not listItem_inTerm)  # otherItems_inTerm are all multiplied items
                    for term in listItem_inTerm:
                        assert isinstance(term, tuple)  # isolated term in format (const, [unknowns])
                        #                                            coeff         unknown addresses unpacked from unknowns list
                        newTerms_toAdd.append( otherItems_inTerm + (term[0],) + tuple(unknownAddress for unknownAddress in term[1]) )
                    break  # process one list item in the term at once

                if hasListItems:
                    for newTerm_toAdd in reversed(newTerms_toAdd):
                        self._LHS_original.insert(termIndex, newTerm_toAdd)
                    self._LHS_original.remove(Term)
                    break  # process one term and break
        # Brackets expanded.

        for term in self._LHS_original:  # each term is a tuple as all brackets expanded above
            constantFactors = []
            unknownFactors = []

            for item in term:  # items within the term are to be multiplied

                if isinstance(item, tuple):
                    # item is an object.attribute address, in form (object, 'attribute')
                    assert isinstance(item[1], str)

                    attribute = getattr_fromAddress(*item)
                    if isNumeric(attribute):
                        # If the object.attribute has a value, add it to constant factors
                        constantFactors.append(attribute)
                    else:
                        # If the object.attribute does not have a value, it is an unknownFactor
                        # TODO - the following check may be accommodated to have equation solved if the high-power term is found in another equation
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
            if unknowns_key not in unknown_termIndices_inEquation:  # TODO: checks by ==, not by identity. Identity should be checked.
                unknown_termIndices_inEquation[unknowns_key] = [termIndex]
            else:
                unknown_termIndices_inEquation[unknowns_key].append(termIndex)

        terms_toPop = []
        for unknowns_key, termIndices_inEquation in unknown_termIndices_inEquation.items():
            if len(termIndices_inEquation) > 1:
                # unknown(s) appears multiple times in equation LHS, e.g. 6*x + 2*x + -3*x = 0 or e.g. 5*x*y + -2*x*y = 0

                # This unknown initially appears at term with index termIndices_inEquation[0] on the LHS of equation
                unknown_otherAppearances = [self.LHS[position] for position in termIndices_inEquation[1:]]  # (*)
                unknown_coefficients_inOtherAppearances = [term[0] for term in unknown_otherAppearances]

                # Modify coefficient of initial appearance - move coefficients from other appearances
                for unknownCoefficient in unknown_coefficients_inOtherAppearances:
                    self.LHS[termIndices_inEquation[0]][0] += unknownCoefficient

                # Remove the subsequent appearances of the unknown since their coefficients have been moved to the initial appearance
                for termIndex in termIndices_inEquation[1:]:
                    terms_toPop.append(termIndex)

        # removing terms in the end b/c if removed in the for loop, line with (*) breaks - list length changed
        for termIndex in reversed(sorted(terms_toPop)):  # reversed, sorted list - to make sure indices remain valid as items are removed
            self.LHS.pop(termIndex)

    def update(self):
        """Iterates over the unknown items in each term, checks if they have become numeric, i.e. have a value now whereas they previously didn't. If so, updates the constant factor
        by multiplying it with the newly determined value and removes it from the unknowns."""

        terms_toRemove = []

        for termIndex, [term_constantFactor, term_unknowns_attributeAddresses] in enumerate(self.LHS):

            # Check if coefficient is 0 - then no need to process any of the unknowns since term will be 0 anyways
            if term_constantFactor == 0:
                terms_toRemove.append(termIndex)
                continue  # continue to next term, no need to resolve the unknowns of this term since the product will be 0 anyways

            # Check if any unknowns became known
            unknowns_toRemove = []
            for unknown_attributeAddress in term_unknowns_attributeAddresses:
                attribute = getattr_fromAddress(*unknown_attributeAddress)
                if isNumeric(attribute):
                    # object.attribute which had previously been identified as unknown now has a value, add it to the constant factor product and remove from the unknowns
                    self.LHS[termIndex][0] *= attribute  # multiply it with the constant factor product
                    unknowns_toRemove.append([termIndex, unknown_attributeAddress])
            for termIndex, unknown_attributeAddress in unknowns_toRemove:  # remove unknowns which have become known in the end
                # removing in the end not to tamper with the iteration of the above loop
                self.LHS[termIndex][1].remove(unknown_attributeAddress)

            # Move constants to RHS
            if self.LHS[termIndex][1] == []:
                # if term has no unknowns, it is a constant, move to RHS
                self.RHS -= self.LHS[termIndex][0]
                self.LHS.pop(termIndex)

        for termIndex in reversed(terms_toRemove):  # reversed - otherwise would tamper with indices of items identified for removal
            self.LHS.pop(termIndex)

        self._gatherUnknowns()

    def get_unknowns(self) -> list:
        unknowns = []
        for [term_constantFactor, term_unknowns_attributeAddresses] in self.LHS:
            assert len(term_unknowns_attributeAddresses) > 0
            unknowns.append(term_unknowns_attributeAddresses)
        return unknowns

    def isolate(self, unknowns: List) -> List:
        """Isolates the provided unknown term in the equation and returns the expression equivalent to the term."""
        expression = []
        constantFactor_ofIsolatedTerm = float('nan')

        for term in self.LHS:  # term = [constantFactor, unknownsList]
            term_constantFactor, term_unknowns_attributeAddresses = term
            if term_unknowns_attributeAddresses == unknowns:
                constantFactor_ofIsolatedTerm = term[0]
            else:
                expression.append( [-1 * term_constantFactor, term_unknowns_attributeAddresses] )  # isolating unknown, so moving all other terms to the other side of the equation, so multiplying by -1
        expression.append( [self.RHS, [(self, '_one')]] )  # adding it in format [ constantFactor, [unknowns] ]
        # expression.append(self.RHS)

        for termIndex, [term_constantFactor, term_unknowns_attributeAddresses] in enumerate(expression):  # dividing all terms moved to the other side by the coefficient of the unknown
            modifiedTerm = list(expression[termIndex])  # list() to create a copy
            modifiedTerm[0] /= constantFactor_ofIsolatedTerm
            expression[termIndex] = tuple(modifiedTerm)

        return expression

    def isSolvable(self):
        if number_ofUnknowns := len(self.get_unknowns()) == 1:
            return True
        return False

    def solve(self):
        assert self.isSolvable()
        assert len(self.LHS) == 1  # all other constant terms must have been moved to the RHS
        return {self.LHS[0][1][0]: self.RHS / self.LHS[0][0]}  # attributeAddress: result - divide RHS by unknown's coefficient

    def solve_and_set(self):
        solution = self.solve()
        unknownAddress = list(solution.keys())[0]
        setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])

    def __str__(self):
        """Returns a string representation of the equation in a more human readable form."""
        termStrings = []
        for term in self.LHS:
            coefficient = term[0]
            unknownSet = term[1]

            termString = str(coefficient) + ' * '
            unknownStrings = []
            for unknown in unknownSet:
                unknownString = unknown[0].__class__.__name__ + '@' + str(id(unknown[0]))[-4:] + '.' + unknown[1]  # last 4 digits of variable ID . attribute name
                unknownStrings.append(unknownString)
            termString += str.join(' * ', unknownStrings)
            termStrings.append(termString)

        termStrings = str.join(' + ', termStrings)
        return termStrings + ' = ' + str(self.RHS)

    def get_asDict(self):
        """Returns a dictionary representation of the equation. Each unknown is a key, and the matching values are their coefficients. RHS (i.e. all constant terms) are tagged with the 'RHS' key."""
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

    def isSolvable(self):
        """Checks if the system of linear equations is solvable by:\n
        (1) Checking if number of equations is equal to number of variables in all equations\n
        (2) Checking if all equations have the same variables\n
        (3) Checking if equations are linear indeed, i.e. single unknowns only, not products of unknowns\n
        (4) Checking rank of system, i.e. if equations are linearly independent"""

        sampleEquation = self.equations[0]
        # Check if (# of equations) == (# of variables in sampleEquation)
        # Check if all equations have the same variables
        if len(self.equations) == len(sampleEquation.get_unknowns()):
            if all(equation.get_unknowns() == sampleEquation.get_unknowns() for equation in self.equations if equation is not sampleEquation): # TODO: Order of unknowns may affect

                # Check if each unknown term has 1 unknown only, i.e. not a product of multiple unknowns, e.g. not 6*x*y but only 6*x.
                for equation in self.equations:
                    for termUnknowns in equation.get_unknowns():  # get_unknowns() returns the list of multiplied unknowns in each term.
                        if len(termUnknowns) != 1:
                            return False

                # Check rank: for system to be solvable, rows must be linearly independent
                coefficientMatrix, _ = self.get_coefficient_constant_matrices()
                if np.linalg.matrix_rank(coefficientMatrix) != len(coefficientMatrix):
                    return False

                return True
        return False

    def solve(self):
        unknowns = self.equations[0].get_unknowns()
        coefficients, constants = self.get_coefficient_constant_matrices()
        solution = np.linalg.solve(a=np.array(coefficients), b=np.array(constants))
        return {unknown[0]: float(solution[unknownIndex]) for unknownIndex, unknown in enumerate(unknowns)}  # unknown[0] since list of multiplied unknowns has only one unknown. Retrieve the unknown from the list

    def get_coefficient_constant_matrices(self) -> [List, List]:
        unknowns = self.equations[0].get_unknowns()
        coefficients, constants = [], []
        for equation in self.equations:
            equation_dict = equation.get_asDict()
            coefficients.append([equation_dict[tuple(unknown)] for unknown in unknowns])
            constants.append(equation_dict['RHS'])
        return coefficients, constants

    def solve_and_set(self):
        solution = self.solve()
        for attributeAddress in solution:
            setattr_fromAddress(object=attributeAddress[0], attributeName=attributeAddress[1], value=solution[attributeAddress])


def updateEquations(equations: List, updatedUnknowns: Set, updateAll: bool = False):
    """Updates the LinearEquations in the list equations if equation contains an unknown from the list updatedUnknowns. Updated all equations if updateAll."""
    for equation in equations:
        if updateAll or any(unknown in equation.get_unknowns() for unknown in updatedUnknowns):
            equation.update()
        updatedUnknowns = set()


def solve_solvableEquations(equations: List):
    """Solves the solvable LinearEquations in **equations** and returns the newly solved unknowns in the **updatedUnknowns** set."""
    solvedEquations = []
    updatedUnknowns = set()

    for equation in equations:
        equation.update()
        if equation.isSolvable():
            solution = equation.solve()
            unknownAddress = list(solution.keys())[0]
            setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
            updatedUnknowns.add(unknownAddress)
            solvedEquations.append(equation)

    for equation in solvedEquations:
        equations.remove(equation)

    return updatedUnknowns


def solve_combination_ofEquations(equations: List, number_ofEquations: int) -> Set:
    """Iterates through combinations of equations (from the equations pool) with the specified number_ofEquations. For each combination, checks if the
    system is solvable. If so, solves it, assigns the unknowns the solution values and removes the solved equations from the _equations pool."""
    updatedUnknowns = set()

    for equationCombination in combinations(equations, number_ofEquations):

        # If any of the equations got solved in a previous iteration and got removed from _equations, skip this combination
        # Combinations are generated beforehand at the beginning of the main for loop.
        if any(equation not in equations for equation in equationCombination):
            continue

        if (system := System_ofLinearEquations(list(equationCombination))).isSolvable():
            solution = system.solve()
            unknownAddresses = list(solution.keys())
            for unknownAddress in unknownAddresses:
                setattr_fromAddress(object=unknownAddress[0], attributeName=unknownAddress[1], value=solution[unknownAddress])
                updatedUnknowns.add(unknownAddress)

            # If system is solved, all equations in the combination is solved. Remove them from equations pool.
            for equation in equationCombination:
                equations.remove(equation)

    return updatedUnknowns


class Logbook:
    def __init__(self):
        self.logbook = []

    def log(self, eventType: str, place, result, workedOn, inRelationTo):
        # EventType
        # Place
        # Result
        # WorkedOn
        # InRelationTo - related device
        self.logbook.append({'eventType': eventType,
                             'place': place,
                             'result': result,
                             'workedOn': workedOn,
                             'inRelationTo': inRelationTo})