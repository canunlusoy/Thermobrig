class FeatureNotAvailableError(Exception):
    def __init__(self, featureName: str = None):
        feature = 'Feature'
        if featureName is not None:
            feature = featureName
        super(FeatureNotAvailableError, self).__init__('{} not implemented'.format(feature))


class NoSaturatedStateError(Exception):
    def __init__(self):
        super(FeatureNotAvailableError, self).__init__()