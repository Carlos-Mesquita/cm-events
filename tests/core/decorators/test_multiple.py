from events import register_multiple, Publisher, Subscriber, Transceiver, component_registry


class MockPublisher(Publisher):
    def __init__(self, pin=None, name=None):
        super().__init__()
        self.pin = pin
        self.name = name


class MockSubscriber(Subscriber):
    def __init__(self, sensor_id=None, interval=None):
        super().__init__()
        self.sensor_id = sensor_id
        self.interval = interval


class MockTransceiver(Transceiver):
    pass


class TestRegisterMultiple:
    def setup_method(self):
        """Clear registry before each test"""
        component_registry.clear()

    def test_register_multiple_instances(self):
        """Test registering multiple instances of same class"""
        instances = [
            {"pin": 18, "name": "button1"},
            {"pin": 19, "name": "button2"},
            {"pin": 20, "name": "button3"}
        ]

        @register_multiple(instances)
        class GPIOPublisher(MockPublisher):
            pass

        # Should have registered all instances
        all_regs = component_registry.get_all_registrations()
        assert len(all_regs['publishers']) == 3

        # Check each registration
        for i, reg in enumerate(all_regs['publishers']):
            assert reg['class_'] == GPIOPublisher
            assert reg['constructor_kwargs'] == instances[i]
            assert reg['auto_start'] is True
            assert reg['component_id'] == f"GPIOPublisher_{i}"

        # Class should have auto_start attribute
        assert GPIOPublisher._auto_start is True

    def test_register_multiple_with_auto_start_false(self):
        """Test auto_start=False parameter"""
        instances = [
            {"sensor_id": "temp_1", "interval": 2.0},
            {"sensor_id": "temp_2", "interval": 1.0}
        ]

        @register_multiple(instances, auto_start=False)
        class SensorSubscriber(MockSubscriber):
            pass

        all_regs = component_registry.get_all_registrations()
        assert len(all_regs['subscribers']) == 2

        # Both should have auto_start=False
        for reg in all_regs['subscribers']:
            assert reg['auto_start'] is False

        assert SensorSubscriber._auto_start is False

    def test_register_multiple_with_custom_id(self):
        """Test custom ID parameter"""
        instances = [
            {"param1": "value1"},
            {"param2": "value2"}
        ]

        @register_multiple(instances, id_="custom_transceiver")
        class CustomTransceiver(MockTransceiver):
            pass

        all_regs = component_registry.get_all_registrations()
        assert len(all_regs['transceivers']) == 2

        # Should use custom ID with index suffix
        expected_ids = ["custom_transceiver_0", "custom_transceiver_1"]
        actual_ids = [reg['component_id'] for reg in all_regs['transceivers']]
        assert actual_ids == expected_ids

    def test_register_multiple_empty_list(self):
        """Test edge case with empty instance list"""

        @register_multiple([])
        class EmptyPublisher(MockPublisher):
            pass

        # Should not register any instances
        all_regs = component_registry.get_all_registrations()
        assert len(all_regs['publishers']) == 0

        # Should still have auto_start attribute
        assert EmptyPublisher._auto_start is True

    def test_register_multiple_preserves_class_functionality(self):
        """Test that decorator doesn't break the class"""
        instances = [{"pin": 1}, {"pin": 2}]

        @register_multiple(instances)
        class PreservedClass(MockPublisher):
            class_var = "preserved"

            def custom_method(self):
                return "custom"

        # Class should work normally
        assert PreservedClass.class_var == "preserved"

        instance = PreservedClass(pin=5, name="test")
        assert instance.custom_method() == "custom"
        assert instance.pin == 5
        assert instance.name == "test"

        # Should have decorator attribute
        assert hasattr(PreservedClass, '_auto_start')

    def test_component_type_detection(self):
        """Test that different component types are handled correctly"""
        instances = [{"param": "value"}]

        @register_multiple(instances)
        class TestPub(MockPublisher):
            pass

        @register_multiple(instances)
        class TestSub(MockSubscriber):
            pass

        @register_multiple(instances)
        class TestTrans(MockTransceiver):
            pass

        all_regs = component_registry.get_all_registrations()

        # Should be in correct categories
        assert len(all_regs['publishers']) == 1
        assert len(all_regs['subscribers']) == 1
        assert len(all_regs['transceivers']) == 1
