import pytest
from unittest.mock import Mock, AsyncMock
from events import Publisher, Event, EventType


class MockEvents(EventType):
    TEST_EVENT = "test_event"


class TestPublisher:
    def test_initialization(self):
        """Test publisher initialization with and without broker"""
        # Without broker
        publisher = Publisher()
        assert publisher._broker is None
        assert publisher._logger is not None

        # With broker
        mock_broker = Mock()
        publisher_with_broker = Publisher(broker=mock_broker)
        assert publisher_with_broker._broker is mock_broker

    @pytest.mark.asyncio
    async def test_publish_with_broker(self):
        """Test publishing when broker is available"""
        mock_broker = AsyncMock()
        publisher = Publisher(broker=mock_broker)
        event = Event(type=MockEvents.TEST_EVENT, source="test", payload={})

        await publisher.publish(event)

        mock_broker.publish.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_publish_without_broker_logs_warning(self, caplog):
        """Test publishing when no broker available logs warning"""
        publisher = Publisher()
        event = Event(type=MockEvents.TEST_EVENT, source="test", payload={})

        await publisher.publish(event)

        assert "not registered with broker" in caplog.text
        assert publisher.__class__.__name__ in caplog.text

    @pytest.mark.asyncio
    async def test_default_run_method(self):
        """Test that default run method exists and doesn't crash"""
        publisher = Publisher()

        # Should not raise - default implementation is pass
        await publisher.run()
