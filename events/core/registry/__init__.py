from typing import Any

from pydantic import BaseModel, Field

from .registration import ComponentRegistration


class ComponentRegistry(BaseModel):
    publishers: list[ComponentRegistration] = Field(default_factory=list, description="Registered publishers")
    subscribers: list[ComponentRegistration] = Field(default_factory=list, description="Registered subscribers")
    transceivers: list[ComponentRegistration] = Field(default_factory=list, description="Registered transceivers")

    def get_all_registrations(self) -> dict[str, list[dict[str, Any]]]:
        return {
            'publishers': [reg.model_dump() for reg in self.publishers],
            'subscribers': [reg.model_dump() for reg in self.subscribers],
            'transceivers': [reg.model_dump() for reg in self.transceivers]
        }

    def add_registration(self, component_type: str, registration_: ComponentRegistration) -> None:
        """Add a registration to the appropriate list"""
        if component_type == 'publishers':
            self.publishers.append(registration_)
        elif component_type == 'subscribers':
            self.subscribers.append(registration_)
        elif component_type == 'transceivers':
            self.transceivers.append(registration_)
        else:
            raise ValueError(f"Unknown component type: {component_type}")

    def clear(self) -> None:
        """Clear all registrations"""
        self.publishers.clear()
        self.subscribers.clear()
        self.transceivers.clear()

    @property
    def total_count(self) -> int:
        """Total number of registered components"""
        return len(self.publishers) + len(self.subscribers) + len(self.transceivers)

component_registry = ComponentRegistry()

__all__ = [
    'component_registry',
    'ComponentRegistration'
]
