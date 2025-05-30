import inspect
from collections.abc import Callable
from typing import Any, TypeVar, cast

from ._register import _register_single_instance
from ._utils import determine_component_type

T = TypeVar('T')

def register(
    *args: type[Any],
    auto_start: bool = True,
    **constructor_kwargs: Any
) -> Callable[[type[T]], type[T]] | type[T]:
    """
    Decorator to register a single instance of a component

    Usage:
        @register
        class MyPublisher(Publisher): ...

        @register(pin=18, threshold=25.0)
        class MyComponent(Publisher): ...
    """
    def decorator(cls: type[T]) -> type[T]:
        component_type = determine_component_type(cls)
        _register_single_instance(cls, constructor_kwargs, auto_start, component_type)
        cls._auto_start = auto_start
        return cls

    if len(args) == 1 and inspect.isclass(args[0]) and not constructor_kwargs:
        return decorator(cast(type[T], args[0]))
    else:
        return decorator