import pytest
from unittest.mock import Mock
from events import Subscriber, Event, EventType


class MockEvents(EventType):
    TEST_EVENT = "test_event"
    ANOTHER_EVENT = "another_event"


class TestSubscriber:
    def test_initialization(self):
        """Test subscriber initialization with and without broker"""
        # Without broker
        subscriber = Subscriber()
        assert subscriber._broker is None
        assert subscriber._pending_subscriptions == []
        assert subscriber._logger is not None

        # With broker
        mock_broker = Mock()
        subscriber_with_broker = Subscriber(broker=mock_broker)
        assert subscriber_with_broker._broker is mock_broker

    def test_subscribe_to_with_broker_immediate_registration(self):
        """Test immediate subscription when broker is available"""
        mock_broker = Mock()
        subscriber = Subscriber(broker=mock_broker)

        subscriber.subscribe_to(MockEvents.TEST_EVENT)

        # Should register immediately with broker
        mock_broker.subscribe.assert_called_once_with(MockEvents.TEST_EVENT, subscriber.handle_event)
        assert subscriber._pending_subscriptions == []

    def test_subscribe_to_without_broker_stores_pending(self):
        """Test pending subscription storage when no broker available"""
        subscriber = Subscriber()

        subscriber.subscribe_to(MockEvents.TEST_EVENT)
        subscriber.subscribe_to(MockEvents.ANOTHER_EVENT)

        # Should store both events for later registration
        assert len(subscriber._pending_subscriptions) == 2
        assert MockEvents.TEST_EVENT in subscriber._pending_subscriptions
        assert MockEvents.ANOTHER_EVENT in subscriber._pending_subscriptions

    def test_register_pending_subscriptions_flow(self):
        """Test the full pending subscription registration flow"""
        mock_broker = Mock()
        subscriber = Subscriber()

        # Subscribe before broker is available
        subscriber.subscribe_to(MockEvents.TEST_EVENT)
        subscriber.subscribe_to(MockEvents.ANOTHER_EVENT)
        assert len(subscriber._pending_subscriptions) == 2

        # Attach broker and register pending subscriptions
        subscriber._broker = mock_broker
        subscriber.register_pending_subscriptions()

        # Should register all pending subscriptions and clear the list
        assert mock_broker.subscribe.call_count == 2
        mock_broker.subscribe.assert_any_call(MockEvents.TEST_EVENT, subscriber.handle_event)
        mock_broker.subscribe.assert_any_call(MockEvents.ANOTHER_EVENT, subscriber.handle_event)
        assert subscriber._pending_subscriptions == []

    def test_register_pending_subscriptions_edge_cases(self):
        """Test edge cases for pending subscription registration"""
        mock_broker = Mock()

        # Test with no pending subscriptions
        subscriber = Subscriber(broker=mock_broker)
        subscriber.register_pending_subscriptions()
        mock_broker.subscribe.assert_not_called()

        # Test without broker (should not raise)
        subscriber_no_broker = Subscriber()
        subscriber_no_broker.subscribe_to(MockEvents.TEST_EVENT)
        subscriber_no_broker.register_pending_subscriptions()  # Should not crash
        assert len(subscriber_no_broker._pending_subscriptions) == 1

    @pytest.mark.asyncio
    async def test_default_handle_event_logs_warning(self, caplog):
        """Test that unhandled events log appropriate warnings"""
        subscriber = Subscriber()
        event = Event(type=MockEvents.TEST_EVENT, source="test", payload={})

        await subscriber.handle_event(event)

        # Should log warning about unhandled event
        assert "Unhandled event" in caplog.text
        assert str(MockEvents.TEST_EVENT) in caplog.text
        assert subscriber.__class__.__name__ in caplog.text

    def test_pending_subscription_behavior_with_duplicates(self):
        """Test that duplicate subscriptions are handled (stored as-is for broker to handle)"""
        subscriber = Subscriber()

        # Subscribe to same event multiple times
        subscriber.subscribe_to(MockEvents.TEST_EVENT)
        subscriber.subscribe_to(MockEvents.TEST_EVENT)

        # Should store duplicates (broker will handle deduplication)
        assert len(subscriber._pending_subscriptions) == 2
        assert all(event == MockEvents.TEST_EVENT for event in subscriber._pending_subscriptions)
