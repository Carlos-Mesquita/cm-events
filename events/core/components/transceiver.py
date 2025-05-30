from typing import TYPE_CHECKING, Optional, TypeVar

from ..event import EventType
from .publisher import Publisher
from .subscriber import Subscriber

if TYPE_CHECKING:  # pragma: no cover
    from ..broker import Broker

T = TypeVar('T', bound=EventType)


class Transceiver(Publisher, Subscriber[T]):
    """Base class for components that both publish and subscribe to events."""
    def __init__(self, broker: Optional["Broker"] = None):
        Publisher.__init__(self, broker)
        Subscriber.__init__(self, broker)
