from typing import TYPE_CHECKING, Generic, Optional, TypeVar

from ..event import Event, EventType
from ._base import Base

if TYPE_CHECKING:  # pragma: no cover
    from ..broker import Broker


T = TypeVar('T', bound=EventType)


class Subscriber(Base, Generic[T]):
    """Base class for anything that subscribes to events"""

    def __init__(self, broker: Optional["Broker"] = None):
        super().__init__(broker)
        self._pending_subscriptions: list[T] = []

    def subscribe_to(self, event_type: T) -> None:
        """Subscribe to an event type"""
        if self._broker:
            self._broker.subscribe(event_type, self.handle_event)
            self._logger.debug(f"Subscribed to {event_type}")
        else:
            # Broker not assigned yet, store for later
            self._pending_subscriptions.append(event_type)

    def register_pending_subscriptions(self) -> None:
        """Register subscriptions that were made before broker was attached"""
        if not self._broker:
            return

        for event_type in self._pending_subscriptions:
            self._broker.subscribe(event_type, self.handle_event)
            self._logger.debug(f"Registered pending subscription to {event_type}")
        self._pending_subscriptions.clear()

    async def handle_event(self, event: Event[T]) -> None:
        """Handle received events, override this"""
        self._logger.warning(f"Unhandled event {event.type} in {self.__class__.__name__}")
