from events import initial_state


class TestInitialStateDecorator:
    def test_basic_functionality(self):
        @initial_state("idle")
        class TestClass:
            pass

        assert TestClass._initial_state == "idle"

    def test_preserves_class_functionality(self):
        @initial_state("active")
        class TestClass:
            def __init__(self, value):
                self.value = value

            def get_value(self):
                return self.value

        # Class should work normally
        instance = TestClass(42)
        assert instance.get_value() == 42
        assert TestClass._initial_state == "active"

    def test_inheritance_behavior(self):
        @initial_state("base")
        class BaseClass:
            pass

        @initial_state("derived")
        class DerivedClass(BaseClass):
            pass

        # Each class should have its own initial state
        assert BaseClass._initial_state == "base"
        assert DerivedClass._initial_state == "derived"

    def test_class_vs_instance_attributes(self):
        @initial_state("test_state")
        class TestClass:
            pass

        instance = TestClass()

        # Should be class attribute, not instance attribute
        assert '_initial_state' not in instance.__dict__
        assert TestClass._initial_state == "test_state"
        # But accessible through inheritance
        assert instance._initial_state == "test_state"
