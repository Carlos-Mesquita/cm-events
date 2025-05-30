from typing import Any

from ..registry import ComponentRegistration, component_registry


def _register_single_instance(
        class_: Any,
        constructor_kwargs: dict[str, Any],
        auto_start: bool,
        component_type: str,
        index: int = -1,
        id_: str | None = None
) -> None:
    component_registry.add_registration(
        component_type,
        ComponentRegistration(**{
            'class': class_,
            'constructor_kwargs': constructor_kwargs,
            'auto_start': auto_start,
            'component_id': (
                id_ if index == -1 else f'{id_}_{index}'
            )
            if id_ else (
                class_.__name__ if index == -1 else f'{class_.__name__}_{index}'
            )
        })
    )
