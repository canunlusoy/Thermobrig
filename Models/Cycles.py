
from Models.Devices import Device

class Cycle:

    def __init__(self):

        self.flows = []
        pass


    def _identify_intersections(self):
        """First / last devices in flow items lists are checked if they appear in multiple flows' items lists. If so, they are inferred to be intersections, i.e. points where flows diverge or combine."""
        intersections, endPoints = [], []
        for flow in self.flows:
            for endPoint in [flow[0], flow[-1]]:
                if isinstance(endPoint, Device):
                    if endPoint not in endPoints:
                        endPoints.append(endPoint)
                    else:
                        intersections.append(endPoint)
        return intersections

    def solve(self):

        for flow in self.flows:
            flow.solve()

        intersections = self._identify_intersections()
        for device in intersections:
            print('Solving intersection: {0}'.format(device))
            

        # find flow intersections
        # solve mixing chambers