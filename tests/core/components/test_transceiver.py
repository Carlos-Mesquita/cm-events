import pytest
from unittest.mock import Mock, AsyncMock
from events import Transceiver, Publisher, Subscriber, Event, EventType


class MockEvents(EventType):
    TEST_EVENT = "test_event"


class TestTransceiver:
    def test_multiple_inheritance_setup(self):
        """Test that Transceiver properly inherits from both parent classes"""
        transceiver = Transceiver()

        # Should be instance of both parent classes
        assert isinstance(transceiver, Publisher)
        assert isinstance(transceiver, Subscriber)

        # Should have key attributes from both
        assert hasattr(transceiver, 'publish')  # Publisher
        assert hasattr(transceiver, 'subscribe_to')  # Subscriber
        assert hasattr(transceiver, '_pending_subscriptions')  # Subscriber
        assert transceiver._pending_subscriptions == []

    def test_initialization_with_broker(self):
        """Test that broker is properly set in both parent classes"""
        mock_broker = Mock()
        transceiver = Transceiver(broker=mock_broker)

        # Both parent __init__ methods should have been called with same broker
        assert transceiver._broker is mock_broker

    @pytest.mark.asyncio
    async def test_publish_and_subscribe_integration(self):
        """Test that both publish and subscribe functionality work together"""
        mock_broker = Mock()
        mock_broker.publish = AsyncMock()
        transceiver = Transceiver(broker=mock_broker)

        # Test subscribe functionality
        transceiver.subscribe_to(MockEvents.TEST_EVENT)
        mock_broker.subscribe.assert_called_once_with(MockEvents.TEST_EVENT, transceiver.handle_event)

        # Test publish functionality
        event = Event(type=MockEvents.TEST_EVENT, source="test", payload={})
        await transceiver.publish(event)
        mock_broker.publish.assert_called_once_with(event)