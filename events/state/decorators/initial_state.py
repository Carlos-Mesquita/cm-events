from collections.abc import Callable
from typing import TypeVar

T = TypeVar('T')

def initial_state(state_name: str) -> Callable[..., Callable[..., T]]:
    """Decorator to set the initial state for the class"""
    def decorator(cls: type[T]) -> type[T]:
        cls._initial_state = state_name
        return cls
    return decorator
