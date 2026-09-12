class FilamentError(RuntimeError):
    """Base exception raised by python-filament."""


class ResourceDestroyedError(FilamentError):
    """Raised when a closed resource is used."""


class BackendUnavailableError(FilamentError):
    """Raised when a requested rendering backend cannot be initialized."""

