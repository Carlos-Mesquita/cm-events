from events import transitions


class TestTransitionsDecorator:
    def test_basic_functionality(self):
        transition_map = {
            "idle": ["active", "error"],
            "active": ["idle", "shutdown"]
        }

        @transitions(transition_map)
        class TestClass:
            pass

        # Should convert lists to sets
        expected = {
            "idle": {"active", "error"},
            "active": {"idle", "shutdown"}
        }
        assert TestClass._transition_map == expected

    def test_preserves_class_functionality(self):
        @transitions({"a": ["b"]})
        class TestClass:
            def __init__(self, value):
                self.value = value

            def get_value(self):
                return self.value

        # Class should work normally
        instance = TestClass(42)
        assert instance.get_value() == 42
        assert TestClass._transition_map == {"a": {"b"}}

    def test_deduplicates_transitions(self):
        # Lists to sets removes duplicates
        transition_map = {
            "state1": ["state2", "state2", "state3"],
        }

        @transitions(transition_map)
        class TestClass:
            pass

        assert TestClass._transition_map == {"state1": {"state2", "state3"}}

    def test_class_vs_instance_attributes(self):
        @transitions({"a": ["b"]})
        class TestClass:
            pass

        instance = TestClass()

        # Should be class attribute, not instance attribute
        assert '_transition_map' not in instance.__dict__
        assert TestClass._transition_map == {"a": {"b"}}
