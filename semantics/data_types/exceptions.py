class InvalidatedReferenceError(Exception):
    """The requested operation cannot be performed because the reference has been released. Use a new reference."""


class ResourceUnavailableError(Exception):
    """The requested access cannot be granted to a resource because it is in use elsewhere."""


class SchemaValidationError(Exception):
    """The validation constraints of the schema were not met by the vertex."""
