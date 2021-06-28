# NOTE: I tried using NewType for the various ID types, but it doesn't support type checking.


class UniqueID(int):
    """Base class for all unique index types."""

    def __repr__(self) -> str:
        return '%s(%s)' % (type(self).__name__, int(self))

    # Pylint warns about the useless call to super(), but it actually causes a TypeError if
    # we take this method definition out and we try to use a UniqueID as a dictionary key.
    # pylint: disable=W0235
    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return super().__eq__(other)

    def __ne__(self, other):
        if not isinstance(other, type(self)):
            return True
        return super().__ne__(other)


class ReferenceID(UniqueID):
    """Unique ID for temporary references to persistent resources."""


class PersistentDataID(UniqueID):
    """Base class for index types that correspond directly to persistent data resources."""


class RoleID(PersistentDataID):
    """Unique ID for roles."""


class VertexID(PersistentDataID):
    """Unique ID for vertices."""


class LabelID(PersistentDataID):
    """Unique ID for labels."""


class EdgeID(PersistentDataID):
    """Unique ID for edges."""
