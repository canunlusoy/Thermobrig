

class Cycle:

    def __init__(self):

        self.flows = []
        pass


class ClosedCycle(Cycle):

    def __init__(self):
        super(ClosedCycle, self).__init__()
        pass


class OpenCycle(Cycle):

    def __init__(self):
        super(OpenCycle, self).__init__()
        pass