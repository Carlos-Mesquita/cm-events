import pytest
import asyncio
from unittest.mock import Mock, patch
from events.core.broker import Broker
from events.core.event import Event, EventType
from events.core.components import Publisher, Subscriber


class MockEvents(EventType):
    TEST_EVENT = "test_event"
    ANOTHER_EVENT = "another_event"


class MockPublisher(Publisher):
    def __init__(self, name="test"):
        super().__init__()
        self.name = name
        self.run_called = False

    async def run(self):
        self.run_called = True
        await asyncio.sleep(0.1)


class MockSubscriber(Subscriber):
    def __init__(self, name="test"):
        super().__init__()
        self.name = name
        self.received_events = []

    async def handle_event(self, event):
        self.received_events.append(event)


class MockStateMachine:
    def __init__(self):
        self._state_machine_running = False

    async def start(self):
        self._state_machine_running = True
        return True

    async def stop(self):
        self._state_machine_running = False

    async def startup(self):
        pass

    async def shutdown(self):
        pass


class TestBroker:
    def test_initialization_defaults(self):
        """Test broker initializes with correct defaults"""
        broker = Broker()

        assert broker._auto_discover is True
        assert broker._running is False
        assert broker._event_queue.maxsize == 500
        assert broker.component_count == 0
        assert broker.pending_events == 0

    def test_initialization_custom_params(self):
        """Test broker initialization with custom parameters"""
        broker = Broker(auto_discover=False, max_queue_size=100)

        assert broker._auto_discover is False
        assert broker._event_queue.maxsize == 100

    def test_register_component_basic(self):
        """Test basic component registration"""
        broker = Broker(auto_discover=False)
        component = MockPublisher()

        broker.register_component(component, "test_pub")

        assert "test_pub" in broker._components
        assert component._broker is broker
        assert broker.component_count == 1

    def test_register_component_duplicate_id_raises_error(self):
        """Test registering duplicate component ID raises error"""
        broker = Broker(auto_discover=False)
        component1 = MockPublisher()
        component2 = MockPublisher()

        broker.register_component(component1, "duplicate")

        with pytest.raises(ValueError, match="already registered"):
            broker.register_component(component2, "duplicate")

    def test_register_component_none_id_uses_class_name(self):
        """Test that None ID uses class name"""
        broker = Broker(auto_discover=False)
        component = MockPublisher()

        broker.register_component(component, None)

        assert "MockPublisher" in broker._components

    def test_register_subscriber_with_pending_subscriptions(self):
        """Test subscriber with pending subscriptions gets registered"""
        broker = Broker(auto_discover=False)
        subscriber = MockSubscriber()

        # Subscribe before broker registration
        subscriber.subscribe_to(MockEvents.TEST_EVENT)
        assert len(subscriber._pending_subscriptions) == 1

        broker.register_component(subscriber, "test_sub")

        # Should register pending subscriptions
        assert len(subscriber._pending_subscriptions) == 0
        assert MockEvents.TEST_EVENT in broker._subscribers

    @pytest.mark.asyncio
    async def test_publish_when_not_running_logs_warning(self, caplog):
        """Test publishing when broker not running logs warning"""
        broker = Broker(auto_discover=False)
        event = Event(type=MockEvents.TEST_EVENT, source="test", payload={})

        await broker.publish(event)

        assert "broker not running" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_start_already_running_logs_warning(self, caplog):
        """Test starting already running broker logs warning"""
        broker = Broker(auto_discover=False)
        broker._running = True

        await broker.start()

        assert "already running" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_stop_not_running_logs_warning(self, caplog):
        """Test stopping non-running broker logs warning"""
        broker = Broker(auto_discover=False)

        await broker.stop()

        assert "not running" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_start_creates_component_tasks(self):
        """Test that start creates tasks for components"""
        broker = Broker(auto_discover=False)
        component = MockPublisher()
        broker.register_component(component, "test_pub")

        await broker.start()

        try:
            assert broker._running is True
            assert broker._event_processor_task is not None
            assert "test_pub" in broker._component_tasks
            assert not broker._component_tasks["test_pub"].done()
        finally:
            await broker.stop()

    @pytest.mark.asyncio
    async def test_start_with_state_machine_component(self):
        """Test starting broker with state machine component"""
        broker = Broker(auto_discover=False)
        component = MockStateMachine()
        broker.register_component(component, "state_machine")

        await broker.start()

        try:
            assert component._state_machine_running is True
        finally:
            await broker.stop()

    @pytest.mark.asyncio
    async def test_stop_cleans_up_properly(self):
        """Test that stop cleans up all resources"""
        broker = Broker(auto_discover=False)
        component = MockPublisher()
        broker.register_component(component, "test_pub")
        broker.subscribe(MockEvents.TEST_EVENT, Mock())

        await broker.start()
        assert broker._running is True
        assert len(broker._components) == 1
        assert len(broker._subscribers) == 1

        await broker.stop()

        assert broker._running is False
        assert len(broker._components) == 0
        assert len(broker._subscribers) == 0
        assert len(broker._component_tasks) == 0

    @pytest.mark.asyncio
    async def test_component_startup_failure_handling(self, caplog):
        """Test handling of component startup failures"""
        broker = Broker(auto_discover=False)

        class FailingComponent(Publisher):
            async def startup(self):
                raise Exception("Startup failed")

        component = FailingComponent()
        broker.register_component(component, "failing")

        await broker.start()
        await asyncio.sleep(0.1)  # Let startup attempt
        await broker.stop()

        assert "Startup failed for failing" in caplog.text

    @pytest.mark.asyncio
    async def test_state_machine_start_failure_logging(self, caplog):
        """Test logging when state machine fails to start"""
        broker = Broker(auto_discover=False)

        class FailingStateMachine:
            def __init__(self):
                self._state_machine_running = False

            async def start(self):
                return False  # Simulate failure

            async def startup(self):
                pass

            async def shutdown(self):
                pass

        component = FailingStateMachine()
        broker.register_component(component, "failing_sm")

        await broker.start()

        try:
            assert "Failed to start state machine for failing_sm" in caplog.text
        finally:
            await broker.stop()

    @pytest.mark.asyncio
    async def test_state_machine_start_exception_logging(self, caplog):
        """Test logging when state machine throws exception on start"""
        broker = Broker(auto_discover=False)

        class ExceptionStateMachine:
            def __init__(self):
                self._state_machine_running = False

            async def start(self):
                raise Exception("Start exception")

            async def startup(self):
                pass

            async def shutdown(self):
                pass

        component = ExceptionStateMachine()
        broker.register_component(component, "exception_sm")

        await broker.start()

        try:
            assert "Error starting state machine for exception_sm" in caplog.text
        finally:
            await broker.stop()

    def test_get_component_info_existing(self):
        """Test getting info for existing component"""
        broker = Broker(auto_discover=False)
        component = MockPublisher()
        broker.register_component(component, "test_pub")

        info = broker.get_component_info("test_pub")

        assert info["id"] == "test_pub"
        assert info["class"] == "MockPublisher"
        assert info["type"] == "Publisher"
        assert info["running"] is False

    def test_get_component_info_nonexistent(self):
        """Test getting info for non-existent component returns None"""
        broker = Broker(auto_discover=False)

        info = broker.get_component_info("nonexistent")

        assert info is None

    def test_utility_methods(self):
        """Test broker utility methods"""
        broker = Broker(auto_discover=False)

        # Test with no components/subscribers
        assert broker.list_components() == []
        assert broker.list_event_types() == []
        assert broker.get_subscriber_count(MockEvents.TEST_EVENT) == 0
        assert broker.is_running is False  # Test is_running property

        # Add components and subscribers
        broker.register_component(MockPublisher(), "pub1")
        broker.register_component(MockSubscriber(), "sub1")
        broker.subscribe(MockEvents.TEST_EVENT, Mock())
        broker.subscribe(MockEvents.TEST_EVENT, Mock())

        assert set(broker.list_components()) == {"pub1", "sub1"}
        assert MockEvents.TEST_EVENT in broker.list_event_types()
        assert broker.get_subscriber_count(MockEvents.TEST_EVENT) == 2

    @patch('events.core.broker.component_registry')
    def test_auto_discover_disabled(self, mock_registry):
        """Test that auto-discovery is disabled when configured"""
        broker = Broker(auto_discover=False)

        broker._auto_discover_components()

        mock_registry.get_all_registrations.assert_not_called()

    @patch('events.core.broker.component_registry')
    def test_auto_discover_enabled(self, mock_registry):
        """Test auto-discovery when enabled"""
        mock_registration = {
            'class': MockPublisher,
            'constructor_kwargs': {'name': 'auto_pub'},
            'auto_start': True,
            'component_id': 'auto_publisher'
        }

        mock_registry.get_all_registrations.return_value = {
            'publishers': [mock_registration],
            'subscribers': [],
            'transceivers': []
        }

        broker = Broker(auto_discover=True)
        # Test the auto-discovery path in start()
        broker._auto_discover_components()

        mock_registry.get_all_registrations.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_discover_called_on_start(self):
        """Test that auto-discovery is called during start when enabled"""
        with patch('events.core.broker.component_registry') as mock_registry:
            mock_registry.get_all_registrations.return_value = {
                'publishers': [],
                'subscribers': [],
                'transceivers': []
            }

            broker = Broker(auto_discover=True)  # Default is True
            await broker.start()

            try:
                # Should have called auto-discovery
                mock_registry.get_all_registrations.assert_called_once()
            finally:
                await broker.stop()

    @pytest.mark.asyncio
    async def test_full_event_flow_integration(self):
        """Integration test for complete publish/subscribe flow"""
        broker = Broker(auto_discover=False)
        subscriber = MockSubscriber()

        # Set up subscription
        subscriber.subscribe_to(MockEvents.TEST_EVENT)
        broker.register_component(subscriber, "test_sub")

        await broker.start()

        try:
            # Publish event
            event = Event(type=MockEvents.TEST_EVENT, source="test", payload={"data": "test"})
            await broker.publish(event)

            # Wait for event processing
            for _ in range(20):  # 2 second timeout
                await asyncio.sleep(0.1)
                if len(subscriber.received_events) > 0:
                    break

            # Verify event was delivered
            assert len(subscriber.received_events) == 1
            assert subscriber.received_events[0].type == MockEvents.TEST_EVENT
            assert subscriber.received_events[0].payload["data"] == "test"
        finally:
            await broker.stop()

    @pytest.mark.asyncio
    async def test_sync_handler_execution(self):
        """Test that synchronous handlers are executed correctly"""
        broker = Broker(auto_discover=False)
        sync_handler = Mock()

        broker.subscribe(MockEvents.TEST_EVENT, sync_handler)
        await broker.start()

        try:
            event = Event(type=MockEvents.TEST_EVENT, source="test", payload={})
            await broker.publish(event)

            # Wait for event processing
            for _ in range(20):
                await asyncio.sleep(0.1)
                if sync_handler.called:
                    break

            sync_handler.assert_called_once_with(event)
        finally:
            await broker.stop()

    @pytest.mark.asyncio
    async def test_handler_exception_logging(self, caplog):
        """Test that handler exceptions are logged"""
        broker = Broker(auto_discover=False)

        def failing_handler(event):
            raise ValueError("Handler failed")

        broker.subscribe(MockEvents.TEST_EVENT, failing_handler)
        await broker.start()

        try:
            event = Event(type=MockEvents.TEST_EVENT, source="test", payload={})
            await broker.publish(event)

            # Wait for event processing
            await asyncio.sleep(0.2)

            assert f"Handler error for event {MockEvents.TEST_EVENT}" in caplog.text
            assert "Handler failed" in caplog.text
        finally:
            await broker.stop()

    @pytest.mark.asyncio
    async def test_no_subscribers_logging(self, caplog):
        """Test logging when no subscribers exist for event"""
        import logging

        broker = Broker(auto_discover=False)
        await broker.start()

        try:
            with caplog.at_level(logging.DEBUG):
                event = Event(type=MockEvents.ANOTHER_EVENT, source="test", payload={})
                await broker.publish(event)

                # Wait for event processing
                await asyncio.sleep(0.2)

            assert f"No subscribers for event type: {MockEvents.ANOTHER_EVENT}" in caplog.text
        finally:
            await broker.stop()

    @pytest.mark.asyncio
    async def test_component_run_method_execution(self):
        """Test that component run methods are executed"""
        broker = Broker(auto_discover=False)
        component = MockPublisher()
        broker.register_component(component, "test_pub")

        await broker.start()

        try:
            # Wait for run method to be called
            for _ in range(20):
                await asyncio.sleep(0.1)
                if component.run_called:
                    break

            assert component.run_called is True
        finally:
            await broker.stop()