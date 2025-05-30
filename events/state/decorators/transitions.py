from collections.abc import Callable
from typing import TypeVar

T = TypeVar('T')

def transitions(transition_map: dict[str, list[str]]) -> Callable[..., Callable[..., T]]:
    """Decorator to define valid state transitions"""
    def decorator(cls: type[T]) -> type[T]:
        cls._transition_map = {state: set(transitions_) for state, transitions_ in transition_map.items()}
        return cls
    return decorator
