import inspect
import typing as py_typing

from numba.core.typing.typeof import typeof
from numba.core import errors, types


class AsNumbaTypeRegistry:
    """
    A registry for python typing declarations.  This registry stores a lookup
    table for simple cases (e.g. int) and a list of functions for more
    complicated cases (e.g. generics like List[int]).

    The as_numba_type registry is meant to work statically on type annotations
    at compile type, not dynamically on instances at runtime. To check the type
    of an object at runtime, see numba.typeof.
    """

    def __init__(self):
        self.lookup = {
            type(example): typeof(example)
            for example in [
                0,
                0.0,
                complex(0),
                "numba",
                True,
                None,
            ]
        }
        self.functions = [self._builtin_infer, self._numba_type_infer]

    def _numba_type_infer(self, py_type):
        if isinstance(py_type, types.Type):
            return py_type

    def _builtin_infer(self, py_type):
        # Cache __origin__ to avoid multiple getattr calls
        origin = getattr(py_type, "__origin__", None)
        # Only check _GenericAlias once
        if not isinstance(py_type, py_typing._GenericAlias):
            return

        # Handle Union
        if origin is py_typing.Union:
            args = py_type.__args__
            if len(args) != 2:
                raise errors.TypingError("Cannot type Union of more than two types")
            arg_1_py, arg_2_py = args
            if arg_2_py is type(None):  # noqa: E721
                t = self.infer(arg_1_py)
                return types.Optional(t)
            elif arg_1_py is type(None):  # noqa: E721
                t = self.infer(arg_2_py)
                return types.Optional(t)
            else:
                raise errors.TypingError(
                    "Cannot type Union that is not an Optional "
                    f"(neither type type {arg_2_py} is not NoneType"
                )

        # Handle list
        if origin is list:
            (element_py,) = py_type.__args__
            elem_type = self.infer(element_py)
            return types.ListType(elem_type)

        # Handle dict
        if origin is dict:
            key_py, value_py = py_type.__args__
            key_type = self.infer(key_py)
            value_type = self.infer(value_py)
            return types.DictType(key_type, value_type)

        # Handle set
        if origin is set:
            (element_py,) = py_type.__args__
            elem_type = self.infer(element_py)
            return types.Set(elem_type)

        # Handle tuple
        if origin is tuple:
            # Use list comprehension for slight speedup (avoid overhead of map)
            args = py_type.__args__
            tys = [self.infer(arg) for arg in args]
            return types.BaseTuple.from_types(tuple(tys))

    def register(self, func_or_py_type, numba_type=None):
        """
        Extend AsNumbaType to support new python types (e.g. a user defined
        JitClass).  For a simple pair of a python type and a numba type, can
        use as a function register(py_type, numba_type).  If more complex logic
        is required (e.g. for generic types), register can also be used as a
        decorator for a function that takes a python type as input and returns
        a numba type or None.
        """
        if numba_type is not None:
            # register used with a specific (py_type, numba_type) pair.
            assert isinstance(numba_type, types.Type)
            self.lookup[func_or_py_type] = numba_type
        else:
            # register used as a decorator.
            assert inspect.isfunction(func_or_py_type)
            self.functions.append(func_or_py_type)

    def try_infer(self, py_type):
        """
        Try to determine the numba type of a given python type.
        We first consider the lookup dictionary.  If py_type is not there, we
        iterate through the registered functions until one returns a numba type.
        If type inference fails, return None.
        """
        result = self.lookup.get(py_type, None)

        for func in self.functions:
            if result is not None:
                break
            result = func(py_type)

        if result is not None and not isinstance(result, types.Type):
            raise errors.TypingError(
                f"as_numba_type should return a numba type, got {result}"
            )
        return result

    def infer(self, py_type):
        # Fast-path: lookup table direct hit
        res = self.lookup.get(py_type)
        if res is not None:
            return res
        result = self.try_infer(py_type)
        if result is None:
            raise errors.TypingError(
                f"Cannot infer numba type of python type {py_type}"
            )
        return result

    def __call__(self, py_type):
        return self.infer(py_type)


as_numba_type = AsNumbaTypeRegistry()
