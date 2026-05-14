"""Service-layer exception types for route-to-service delegation."""


class ServiceValidationError(Exception):
    """Raised when incoming domain input fails validation."""


class ServiceAuthorizationError(Exception):
    """Raised when a caller lacks permission to perform an operation."""


class ServiceInvariantError(Exception):
    """Raised when business invariants are violated during processing."""
