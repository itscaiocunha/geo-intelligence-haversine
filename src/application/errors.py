class AccessDenied(Exception):
    """Base class for authentication and authorization failures. The message is client-facing."""


class MissingCredentials(AccessDenied):
    pass


class InvalidCredentials(AccessDenied):
    pass


class InsufficientPermissions(AccessDenied):
    pass
