from typing import List
from Models.States import StatePure
from Models.Cycles import Cycle

class SolutionTracker:

    def __init__(self, cycle: Cycle):

        self.stateTracker = {}

        for flow in cycle.flows:
            for state in flow.states:

                if state not in self.stateTracker:
                    self.trackState(state)

                self.stateTracker[state]['flows'].add(flow)



    def trackState(self, state: StatePure):
        self.stateTracker[state] = {'flows': set()}