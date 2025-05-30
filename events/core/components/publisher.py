from typing import Generic, TypeVar

from ..event import Event, EventType
from ._base import Base

T = TypeVar('T', bound=EventType)


class Publisher(Base, Generic[T]):
    """Base class for anything that publishes events"""

    async def publish(self, event: Event[T]) -> None:
        """Publish an event to the broker"""
        if self._broker is None:
            self._logger.warning(f"Publisher {self.__class__.__name__} not registered with broker")
            return
        await self._broker.publish(event)

    async def run(self) -> None:
        """Publisher main loop if you need one, else just setup a callback in startup"""
        pass
