from events import Event, EventType


class MockEvents(EventType):
    SENSOR_DATA = "sensor_data"
    SYSTEM_ERROR = "system_error"


class TestEvent:
    def test_basic_event_creation(self):
        event = Event(type=MockEvents.SENSOR_DATA, source="temp_sensor", payload={"temp": 25.5})

        assert event.type == MockEvents.SENSOR_DATA
        assert event.source == "temp_sensor"
        assert event.payload == {"temp": 25.5}
        assert isinstance(event.timestamp, float)

    def test_event_type_system_works(self):
        # Test that EventType extension works correctly
        event = Event(type=MockEvents.SYSTEM_ERROR, source="cpu_monitor", payload={"error": "overheating"})

        assert event.type == "system_error"  # String value
        assert event.type == MockEvents.SYSTEM_ERROR  # Enum equality

    def test_timestamp_ordering_for_sequencing(self):
        event1 = Event(type=MockEvents.SENSOR_DATA, source="sensor1", payload={})
        event2 = Event(type=MockEvents.SENSOR_DATA, source="sensor2", payload={})

        # Later events should have later timestamps
        assert event2.timestamp >= event1.timestamp