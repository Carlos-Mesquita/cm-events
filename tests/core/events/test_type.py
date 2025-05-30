from events import Event, EventType


class TestEventType:
    def test_event_type_is_empty_enum(self):
        # Verify it's an empty enum that can be extended
        assert len(EventType) == 0

        # Should be able to create custom enum that extends it
        class CustomEvents(EventType):
            TEST_EVENT = "test_event"
            ANOTHER_EVENT = "another_event"

        assert len(CustomEvents) == 2
        assert CustomEvents.TEST_EVENT == "test_event"
        assert CustomEvents.ANOTHER_EVENT == "another_event"

    def test_event_type_inheritance(self):
        class MyEvents(EventType):
            SENSOR_DATA = "sensor_data"

        # Should work with Event class
        event = Event(type=MyEvents.SENSOR_DATA, source="sensor", payload={})
        assert event.type == "sensor_data"
