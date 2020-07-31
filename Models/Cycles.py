

class Cycle:

    def __init__(self):

        self.flows = []
        pass


    def solve(self):

        for flow in self.flows:
            flow.solve()

        # find flow intersections
        # solve mixing chambers