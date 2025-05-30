import pytest
from events.core.decorators._utils import determine_component_type
from events import Transceiver, Publisher, Subscriber


class MockPublisher(Publisher):
    pass


class MockSubscriber(Subscriber):
    pass


class MockTransceiver(Transceiver):
    pass


class InvalidClass:
    pass


class TestDetermineComponentType:
    def test_publisher_type(self):
        """Test publisher class returns correct type"""
        result = determine_component_type(MockPublisher)
        assert result == 'publishers'

    def test_subscriber_type(self):
        """Test subscriber class returns correct type"""
        result = determine_component_type(MockSubscriber)
        assert result == 'subscribers'

    def test_transceiver_type(self):
        """Test transceiver class returns correct type"""
        result = determine_component_type(MockTransceiver)
        assert result == 'transceivers'

    def test_transceiver_precedence(self):
        """Test that transceiver takes precedence over publisher/subscriber"""
        # Transceiver inherits from both Publisher and Subscriber
        # Should return 'transceivers' since it's checked first
        result = determine_component_type(Transceiver)
        assert result == 'transceivers'

    def test_invalid_class_raises_error(self):
        """Test invalid class raises ValueError with proper message"""
        with pytest.raises(ValueError) as exc_info:
            determine_component_type(InvalidClass)

        assert "must inherit from Publisher, Subscriber, or Transceiver" in str(exc_info.value)
        assert "InvalidClass" in str(exc_info.value)

    def test_non_class_input_raises_error(self):
        """Test non-class input raises TypeError"""
        with pytest.raises(TypeError):
            determine_component_type("not_a_class")

        with pytest.raises(TypeError):
            determine_component_type(None)
