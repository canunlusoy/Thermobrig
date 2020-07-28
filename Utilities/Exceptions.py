class FeatureNotAvailableError(Exception):
    def __init__(self, featureName: str = None):
        feature = 'Feature'
        if featureName is not None:
            feature = featureName
        super(FeatureNotAvailableError, self).__init__('{} not implemented'.format(feature))


class NoSaturatedStateError(Exception):
    def __init__(self):
        super(NoSaturatedStateError, self).__init__()


class NeedsExtrapolationError(Exception):
    def __init__(self, message: str):
        super(NeedsExtrapolationError, self).__init__(message)
