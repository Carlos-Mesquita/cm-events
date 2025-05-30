from asyncio import CancelledError, Queue, Task, create_task, iscoroutinefunction, sleep
from collections.abc import Callable
from contextlib import suppress
from logging import getLogger
from typing import Any, Generic, TypeVar

from .components import Publisher, Subscriber, Transceiver
from .event import Event, EventType
from .registry import component_registry

T = TypeVar('T', bound=EventType)
Component = Publisher | Subscriber | Transceiver


class Broker(Generic[T]):
    """Event-driven pub/sub broker with auto-discovery"""

    def __init__(self, auto_discover: bool = True, max_queue_size: int = 500):
        self._event_queue: Queue = Queue(maxsize=max_queue_size)
        self._subscribers: dict[T, list[Callable]] = {}
        self._components: dict[str, Component] = {}
        self._running = False
        self._event_processor_task: Task | None = None
        self._component_tasks: dict[str, Task] = {}
        self._logger = getLogger(__name__)
        self._auto_discover = auto_discover

    def _auto_discover_components(self) -> None:
        """Auto-discover and instantiate all registered components"""
        if not self._auto_discover:
            return

        self._logger.info("Auto-discovering registered components...")

        for _, registrations in component_registry.get_all_registrations().items():
            for registration_info in registrations:
                if registration_info['auto_start']:
                    component = self._instantiate_component(registration_info)
                    component_id = registration_info['component_id']
                    self._register_component(component, component_id)
                    self._logger.debug(f"Auto-registered {component_id}")

    @staticmethod
    def _instantiate_component(registration_info: dict) -> Any:
        """Instantiate a component from registration info"""
        cls = registration_info['class']
        kwargs = registration_info['constructor_kwargs']
        instance = cls(**kwargs)
        return instance

    def _register_component(self, component: Component, component_id: str) -> None:
        """Register a component and set up pub/sub connections"""
        if component_id in self._components:
            raise ValueError(f"Component ID '{component_id}' already registered")
        self._components[component_id] = component
        component._broker = self
        if hasattr(component, 'register_pending_subscriptions'):
            component.register_pending_subscriptions()
        self._logger.debug(f"Registered component: {component_id}")

    def register_component(self, component: Component, component_id: str) -> None:
        """Manually register a component"""
        if component_id is None:
            component_id = component.__class__.__name__
        self._register_component(component, component_id)

    def subscribe(self, event_type: T, handler: Callable) -> None:
        """Subscribe a handler to an event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        self._logger.debug(f"Subscribed handler to event type: {event_type}")

    async def publish(self, event: Event[T]) -> None:
        """Publish an event to the queue"""
        if not self._running:
            self._logger.warning("Cannot publish event, broker not running")
            return

        await self._event_queue.put(event)
        self._logger.debug(f"Published event: {event.type}")

    async def _process_events(self) -> None:
        """Main event processing loop"""
        self._logger.info("Event processor started")

        while self._running:
            try:
                # Get event from queue
                event = await self._event_queue.get()

                # Find subscribers for this event type
                if event.type in self._subscribers:
                    handlers = self._subscribers[event.type]
                    self._logger.debug(
                        f"Processing event {event.type} with {len(handlers)} handlers"
                    )

                    # Call all handlers for this event type
                    for handler in handlers:
                        try:
                            if iscoroutinefunction(handler):
                                await handler(event)
                            else:
                                handler(event)
                        except Exception as e:
                            self._logger.error(f"Handler error for event {event.type}: {e}")
                else:
                    self._logger.debug(f"No subscribers for event type: {event.type}")

                # Mark task as done
                self._event_queue.task_done()

            except Exception as e:
                self._logger.error(f"Event processing error: {e}")

    async def _run_component(self, component: Component, component_id: str) -> None:
        """Run a component's main loop if it has one"""
        try:
            try:
                await component.startup()
                self._logger.debug(f"Started up component: {component_id}")
            except Exception as e:
                self._logger.error(f"Startup failed for {component_id}: {e}")
                raise

            if not isinstance(component, Subscriber) and hasattr(component, 'run') and callable(component.run):
                self._logger.info(f"Starting component run loop: {component_id}")
                await component.run()
            else:
                # Component doesn't have a run method, just keep it alive
                self._logger.debug(f"Component {component_id} has no run method, keeping alive...")
                while self._running:
                    await sleep(1)
        except CancelledError:
            self._logger.info(f"Component {component_id} cancelled")
            raise
        except Exception as e:
            self._logger.error(f"Component {component_id} crashed: {e}")
        finally:
            try:
                await component.shutdown()
                self._logger.debug(f"Shut down component: {component_id}")
            except Exception as e:
                self._logger.error(f"Error during {component_id} shutdown: {e}")

    async def start(self) -> None:
        """Start the broker and all components"""
        if self._running:
            self._logger.warning("Broker already running")
            return

        self._running = True

        if self._auto_discover:
            self._auto_discover_components()

        self._event_processor_task = create_task(self._process_events())

        # Start all components that need running
        for component_id, component in self._components.items():
            task = create_task(self._run_component(component, component_id))
            self._component_tasks[component_id] = task

        # Start state machines for components that have them
        for component_id, component in self._components.items():
            if hasattr(component, 'start') and hasattr(component, '_state_machine_running'):
                try:
                    started = await component.start()
                    if started:
                        self._logger.info(f"Started state machine for {component_id}")
                    else:
                        self._logger.warning(f"Failed to start state machine for {component_id}")
                except Exception as e:
                    self._logger.error(f"Error starting state machine for {component_id}: {e}")

        self._logger.info(f"Broker started with {len(self._components)} components")

    async def stop(self) -> None:
        """Stop the broker and all components"""
        if not self._running:
            self._logger.warning("Broker not running")
            return

        self._running = False

        # Stop state machines for components that have them
        for component_id, component in self._components.items():
            if hasattr(component, 'stop'):
                try:
                    await component.stop()
                    self._logger.info(f"Stopped state machine for {component_id}")
                except Exception as e:
                    self._logger.error(f"Error stopping state machine for {component_id}: {e}")

        # Stop all component tasks
        for component_id, task in self._component_tasks.items():
            self._logger.debug(f"Stopping component: {component_id}")
            task.cancel()
            with suppress(CancelledError):
                await task

        self._component_tasks.clear()

        # Stop event processor
        if self._event_processor_task:
            self._event_processor_task.cancel()
            with suppress(CancelledError):
                await self._event_processor_task

        # Wait for any remaining events to be processed
        await self._event_queue.join()

        self._components.clear()
        self._subscribers.clear()

        self._logger.info("Broker stopped")

    # Utility methods for debugging and monitoring
    def get_component_info(self, component_id: str) -> dict[str, Any] | None:
        """Get information about a component"""
        if component_id not in self._components:
            return None

        component = self._components[component_id]
        return {
            "id": component_id,
            "class": component.__class__.__name__,
            "type": "Publisher" if isinstance(component, Publisher) else "Subscriber",
            "running": (
                component_id in self._component_tasks and
                not self._component_tasks[component_id].done()
            )
        }

    def list_components(self) -> list[str]:
        """List all registered component IDs"""
        return list(self._components.keys())

    def list_event_types(self) -> list[T]:
        """List all subscribed event types"""
        return list(self._subscribers.keys())

    def get_subscriber_count(self, event_type: T) -> int:
        """Get number of subscribers for an event type"""
        return len(self._subscribers.get(event_type, []))

    @property
    def is_running(self) -> bool:
        """Check if broker is running"""
        return self._running

    @property
    def component_count(self) -> int:
        """Get number of registered components"""
        return len(self._components)

    @property
    def pending_events(self) -> int:
        """Get number of pending events in queue"""
        return self._event_queue.qsize()
