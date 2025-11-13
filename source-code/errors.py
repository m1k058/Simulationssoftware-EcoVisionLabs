# standart exception
class AppError(Exception):
    """Base class for all application-level errors."""
    prefix = "ERROR:"

    def __str__(self):
        return f"{self.prefix} {super().__str__()}"


class WarningMessage(Warning):
    """Used for non-critical warnings shown to the user."""


# configuration and file error
class ConfigError(AppError):
    """Raised when configuration file or structure is invalid."""
    prefix = "CONFIG ERROR:"


class FileLoadError(AppError):
    """Raised when a file cannot be found or loaded properly."""
    prefix = "FILE ERROR:"


class DataframeNotFoundError(AppError):
    """Raised when a requested dataframe does not exist."""
    prefix = "DATAFRAME NOT FOUND:"


class PlotNotFoundError(AppError):
    """Raised when a requested plot does not exist."""
    prefix = "PLOT NOT FOUND:"


class DataProcessingError(AppError):
    """Raised for general issues during data processing or computation."""
    prefix = "PROCESSING ERROR:"
