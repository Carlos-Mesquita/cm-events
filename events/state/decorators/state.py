from asyncio import sleep
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

P = TypeVar('P')
T = TypeVar('T')

def state(
        state_name: str, poll_interval: float = 0.1
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """State decorator with polling support."""
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Call the original state method
            result = await func(self, *args, **kwargs)

            # If state doesn't return a transition, poll at configured interval
            if result is None or result == self._current_state:
                current_interval = getattr(self, f'_{state_name}_poll_interval', poll_interval)
                await sleep(current_interval)

            return result

        wrapper._is_state = True
        wrapper._state_name = state_name
        wrapper._default_poll_interval = poll_interval
        return wrapper

    return decorator