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


class DataVerificationError(Exception):
    def __init__(self, availableValue: float, alternateValue: float):
        message = 'Initial value of {0} compared with {1} for verification. Two values are not within acceptable proximity. ' \
                  'The compared value is obtained using a different method / source, and is expected to match the already available value.'.format(availableValue, alternateValue)
        super(DataVerificationError, self).__init__(message)