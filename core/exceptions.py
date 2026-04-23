class UnsupportedFileTypeError(ValueError):
    pass


class UnsupportedOutputFormatError(ValueError):
    pass


class FileTooLargeError(ValueError):
    pass


class EmptyExtractedTextError(ValueError):
    pass


class TextTooLargeError(ValueError):
    pass


class TooManyFragmentsError(ValueError):
    pass


class InvalidPercentageError(ValueError):
    pass