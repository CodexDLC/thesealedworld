class CabinetError(Exception):
    """Base error for FastAPI Cabinet setup failures."""


class CabinetRegistrationError(CabinetError):
    """Raised when an admin declaration cannot be registered."""


class CabinetDuplicateKeyError(CabinetRegistrationError):
    """Raised when two admin declarations use the same key."""


class CabinetModuleLoadError(CabinetError):
    """Raised when a configured cabinet module cannot be loaded."""


class CabinetProviderError(CabinetError):
    """Raised when a widget provider cannot be resolved or validated."""
