"""
Exception hierarchy.

All exceptions defined in the package have their home here.
"""


class InvalidatedReferenceError(Exception):
    """The requested operation cannot be performed because the reference has been
    released. Use a new reference."""


class ResourceUnavailableError(Exception):
    """The requested access cannot be granted to a resource because it is in use
    elsewhere."""


class SchemaValidationError(Exception):
    """The validation constraints of the schema were not met by the vertex."""


class ConnectionClosedError(ConnectionError):
    """Attempting to use a connection that has already been closed."""


class InvalidThreadError(Exception):
    """Transaction used from a different thread than the one that created it."""
