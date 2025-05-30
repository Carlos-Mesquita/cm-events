from typing import Any

from ..components import Publisher, Subscriber, Transceiver


def determine_component_type(class_: Any) -> str:
    if issubclass(class_, Transceiver):
        component_type = 'transceivers'
    elif issubclass(class_, Publisher):
        component_type = 'publishers'
    elif issubclass(class_, Subscriber):
        component_type = 'subscribers'
    else:
        raise ValueError(
            f"Class {class_.__name__} must inherit from Publisher, Subscriber, or Transceiver"
        )
    return component_type
