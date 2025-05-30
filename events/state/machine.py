import time
from asyncio import CancelledError, Task, create_task
from collections.abc import Callable
from contextlib import suppress
from logging import getLogger
from typing import Generic, TypeVar

from ..core.event import Event, EventType

T = TypeVar('T', bound=EventType)


class StateMachine(Generic[T]):
    """
    Async state machine that runs a loop, executing the current state method
    and transitioning to new states based on return values
    """

    _transition_map: dict[str, set[str]]
    _initial_state: str | None
    _state_handlers: dict[str, Callable]

    def __init__(self, state_change_event_type: T | None = None, max_consecutive_errors: int = 5):
        # Core state tracking
        self._current_state: str | None = None
        self._previous_state: str | None = None
        self._state_start_time: float = 0

        # State configuration from decorators
        self._state_handlers: dict[str, Callable] = {}
        self._transition_map: dict[str, set[str]] = getattr(self.__class__, '_transition_map', {})
        self._initial_state: str = getattr(self.__class__, '_initial_state', None)

        # Runtime control
        self._state_machine_running = False
        self._state_task: Task | None = None
        self._current_event: Event[T] | None = None

        self._logger = getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        # Auto-discover state methods
        self._discover_states()

        # If this is a subscriber, intercept events for state machine
        if hasattr(self, 'handle_event'):
            self._original_handle_event = self.handle_event  # type: ignore[has-type]
            self.handle_event = self._state_aware_handle_event

        self._consecutive_errors = 0
        self._max_consecutive_errors = max_consecutive_errors
        self._state_change_event_type = state_change_event_type

    def _discover_states(self) -> None:
        """Find methods decorated with @state"""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_is_state'):
                state_name = attr._state_name
                self._state_handlers[state_name] = attr
                self._logger.debug(f"Discovered state: {state_name}")

    async def _state_aware_handle_event(self, event: Event[T]) -> None:
        """Intercept events and make them available to current state"""
        # Store current event for state methods to access
        self._current_event = event

        # Also call original handler if it exists
        if hasattr(self, '_original_handle_event'):
            await self._original_handle_event(event)

    def _is_valid_transition(self, from_state: str, to_state: str) -> bool:
        """Check if transition is allowed by transition map"""
        if not self._transition_map:
            return True  # No restrictions if no map defined

        allowed_states = self._transition_map.get(from_state, set())
        return to_state in allowed_states

    async def transition_to(self, new_state: str) -> bool:
        """Transition to a new state"""
        if new_state not in self._state_handlers:
            self._logger.error(f"Unknown state: {new_state}")
            return False

        if self._current_state and not self._is_valid_transition(self._current_state, new_state):
            self._logger.error(f"Invalid transition from {self._current_state} to {new_state}")
            return False

        # Update state tracking
        self._previous_state = self._current_state
        self._current_state = new_state
        self._state_start_time = time.monotonic()

        self._logger.info(f"Transitioned from {self._previous_state} to {self._current_state}")

        # Publish state change if this is a publisher
        if hasattr(self, 'publish') and self._state_change_event_type:
            await self.publish(
                Event(
                    type=self._state_change_event_type,
                    source=self.__class__.__name__,
                    payload={
                        'previous_state': self._previous_state,
                        'current_state': self._current_state,
                        'timestamp': self._state_start_time
                    }
                )
            )

        return True

    async def _run_state_machine(self) -> None:
        """State machine loop. State handlers return: str (next state), None (stay), or False (stop)."""
        self._state_machine_running = True

        while self._state_machine_running and self._current_state:
            try:
                # Get current state handler
                handler = self._state_handlers[self._current_state]

                # Call state method, the state method decorator handles polling so
                # don't worry about this blocking
                if self._current_event:
                    next_state = await handler(self._current_event)
                    self._current_event = None  # Clear after use
                else:
                    next_state = await handler()

                # Handle state transition
                if isinstance(next_state, str) and next_state != self._current_state:
                    if next_state != 'error':
                        self._consecutive_errors = 0
                    await self.transition_to(next_state)
                elif next_state is False:
                    # State returned False, stop machine
                    self._logger.info("State machine stopped by state method")
                    break
            except Exception as original_error:
                self._consecutive_errors += 1
                if self._consecutive_errors >= self._max_consecutive_errors:
                    self._logger.critical("Too many consecutive errors, stopping state machine")
                    break

                self._logger.error(
                    f"State machine error in {self._current_state}: {original_error}"
                )
                if 'error' in self._state_handlers:
                    try:
                        await self.transition_to('error')
                        continue
                    except Exception as transition_error:
                        self._logger.critical(f"Failed to transition to error state: {transition_error}")
                        break
                else:
                    self._logger.info("No error state handler, shutting down ...")
                    break

    async def start(self) -> bool:
        """Start the state machine"""
        if not self._current_state:
            if self._initial_state:
                await self.transition_to(self._initial_state)
            else:
                self._logger.error("No initial state defined")
                return False

        if not self._state_task or self._state_task.done():
            self._state_task = create_task(self._run_state_machine())
            self._logger.info("State machine started")
            return True
        else:
            self._logger.warning("State machine already running")
            return False

    async def stop(self) -> None:
        """Stop the state machine"""
        self._state_machine_running = False
        if self._state_task:
            self._state_task.cancel()
            with suppress(CancelledError):
                await self._state_task
        self._logger.info("State machine stopped")

    async def restart(self) -> None:
        """Reset error count and restart state machine"""
        self._consecutive_errors = 0
        await self.start()

    def set_poll_interval(self, state_name: str, interval: float) -> None:
        """Change polling interval for a specific state at runtime"""
        setattr(self, f'_{state_name}_poll_interval', interval)
        self._logger.debug(f"Set poll interval for {state_name} to {interval}s")

    def get_poll_interval(self, state_name: str) -> float:
        """Get current polling interval for a state"""
        if hasattr(self, f'_{state_name}_poll_interval'):
            interval = getattr(self, f'_{state_name}_poll_interval')
            return float(interval)

        # Get default from the decorated method
        handler = self._state_handlers.get(state_name)
        if handler and hasattr(handler, '_default_poll_interval'):
            return float(handler._default_poll_interval)

        return 0.1  # Fallback

    # For introspection/debugging/monitoring
    @property
    def current_state(self) -> str | None:
        return self._current_state

    @property
    def previous_state(self) -> str | None:
        return self._previous_state

    @property
    def state_uptime(self) -> float:
        if self._current_state:
            return time.monotonic() - self._state_start_time
        return 0.0

    @property
    def available_states(self) -> set[str]:
        return set(self._state_handlers.keys())

    @property
    def is_running(self) -> bool:
        return bool(
            self._state_machine_running and
            self._state_task and
            not self._state_task.done()
        )