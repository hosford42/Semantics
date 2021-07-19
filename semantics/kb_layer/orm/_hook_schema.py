import importlib
import logging
import typing

from semantics.kb_layer import schema
from semantics.kb_layer import schema_registry

if typing.TYPE_CHECKING:
    pass


_logger = logging.getLogger(__name__)


@schema_registry.register
class Hook(schema.Schema):
    """A hook is a callback function stored persistently in the graph."""

    def __repr__(self) -> str:
        name = self.vertex.name or '<unnamed>'
        return '<%s#%s(%s)>' % (type(self).__name__, int(self._vertex.index), name)

    @schema.validation('{schema} must have an associated module_name attribute.')
    def has_module_name(self) -> bool:
        """Whether the hook has an associated callback module name."""
        return self.module_name is not None

    @schema.validation('{schema} must have an associated function_name attribute.')
    def has_function_name(self) -> bool:
        """Whether the hook has an associated callback function name."""
        return self.function_name is not None

    @schema.validation('{schema} must refer to a valid Python module.')
    def has_valid_module(self) -> bool:
        """Whether the hook's module can be located."""
        return self.get_module() is not None

    @schema.validation('{schema} must refer to a valid Python function.')
    def has_valid_function(self) -> bool:
        """Whether the hook's function can be located."""
        return self.get_function() is not None

    @property
    def module_name(self) -> typing.Optional[str]:
        """The name of the module in which the hook's function resides."""
        module_name = self._vertex.get_data_key('module_name')
        if module_name and isinstance(module_name, str):
            return module_name
        return None

    @property
    def function_name(self) -> typing.Optional[str]:
        """The name of the function the hook refers to."""
        function_name = self._vertex.get_data_key('function_name')
        if function_name and isinstance(function_name, str):
            return function_name
        return None

    def get_module(self) -> typing.Optional[typing.Any]:
        """Look up and return the hook's module."""
        module_name = self.module_name
        if not module_name:
            return None
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError:
            return None

    def get_function(self) -> typing.Optional[typing.Callable]:
        """Look up and return the hook's callback."""
        module = self.get_module()
        if not module:
            return None
        function_name = self.function_name
        if not function_name:
            return None
        value = module
        for name in function_name.split('.'):
            value = getattr(value, name, None)
        if callable(value):
            return value
        return None

    def __call__(self, *args, **kwargs) -> typing.Any:
        """Call the hook as a function."""
        callback = self.get_function()
        if callback is None:
            raise ValueError("Callback is undefined for this hook. Module: %r. Name: %r." %
                             (self.module_name, self.function_name))
        return callback(*args, **kwargs)
