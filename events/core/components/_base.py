from logging import getLogger
from typing import TYPE_CHECKING, Generic, Optional, TypeVar

from ..event import EventType

if TYPE_CHECKING: # pragma: no cover
    from ..broker import Broker

T = TypeVar('T', bound=EventType)


class Base(Generic[T]):
    """Base class with lifecycle methods"""

    def __init__(self, broker: Optional["Broker"] = None):
        self._broker = broker
        self._logger = getLogger(self.__class__.__module__)

    async def startup(self) -> None:
        """Override this if you need to do some stuff at the beginning of the component's lifecycle"""
        pass

    async def shutdown(self) -> None:
        """Override this if you need to do some stuff at the end of the component's lifecycle"""
        pass
