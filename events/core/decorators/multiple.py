from collections.abc import Callable
from typing import Any, TypeVar

from ._register import _register_single_instance
from ._utils import determine_component_type

T = TypeVar('T')

def register_multiple(
    instances: list[dict[str, Any]],
    auto_start: bool = True,
    id_: str | None = None
) -> Callable[[type[T]], type[T]]:
    """
    Decorator to register multiple instances of the same component class

    Usage:
        @register_multiple([
            {"pin": 18, "name": "button1"},
            {"pin": 19, "name": "button2"},
            {"pin": 20, "name": "emergency"}
        ])
        class GPIOPublisher(Publisher): ...

        @register_multiple([
            {"sensor_id": "temp_1", "interval": 2.0},
            {"sensor_id": "temp_2", "interval": 1.0},
            {"sensor_id": "humidity_1", "interval": 5.0}
        ])
        class SensorPublisher(Publisher): ...
    """
    def decorator(cls: type[T]) -> type[T]:
        component_type = determine_component_type(cls)
        for i, instance_kwargs in enumerate(instances):
            _register_single_instance(cls, instance_kwargs, auto_start, component_type, i, id_)
        cls._auto_start = auto_start
        return cls
    return decorator
