from collections import UserList
from typing import List, Iterable, Callable


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