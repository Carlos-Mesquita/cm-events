from typing import Any

from pydantic import BaseModel, Field


class ComponentRegistration(BaseModel):
    """Registration information for a component"""
    class_: type = Field(..., alias="class", description="Component class")
    constructor_kwargs: dict[str, Any] = Field(default_factory=dict, description="Constructor arguments")
    auto_start: bool = Field(default=True, description="Whether to auto-start this component")
    component_id: str = Field(..., description="Unique identifier for the component")
