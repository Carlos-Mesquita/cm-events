from time import monotonic
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from .type import EventType

T = TypeVar('T', bound=EventType)


class Event(BaseModel, Generic[T]):
    """Uses monotonic time for precision. Add timezone info to payload if needed."""
    type: T
    payload: Any
    source: str
    timestamp: float = Field(default_factory=monotonic)


__all__ = [
    'Event',
    'EventType'
]
