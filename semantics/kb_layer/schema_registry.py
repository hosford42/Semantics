import typing

if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema

    SchemaSubclass = typing.TypeVar('SchemaSubclass', bound=schema.Schema)


_SCHEMA_REGISTRY: typing.Dict[str, typing.Type['schema.Schema']] = {}


def register(schema_type: typing.Type['SchemaSubclass']) -> typing.Type['SchemaSubclass']:
    """Decorator for schema subclasses to register them with their associated role names."""
    role_name = schema_type.role_name()
    previously_registered = _SCHEMA_REGISTRY.get(role_name, None)
    if previously_registered is None:
        _SCHEMA_REGISTRY[role_name] = schema_type
    elif previously_registered is not schema_type:
        raise KeyError("Role %s is already mapped to schema %s." %
                       (role_name, previously_registered))
    return schema_type


def get_registered_schema(role_name: str) -> typing.Optional[typing.Type['schema.Schema']]:
    return _SCHEMA_REGISTRY.get(role_name, None)
