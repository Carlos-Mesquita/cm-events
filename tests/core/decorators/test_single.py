import pytest
from events import register, Publisher, Subscriber, Transceiver, component_registry


class MockPublisher(Publisher):
    def __init__(self, param1=None, param2=None):
        super().__init__()
        self.param1 = param1
        self.param2 = param2


class MockSubscriber(Subscriber):
    def __init__(self, config=None):
        super().__init__()
        self.config = config


class MockTransceiver(Transceiver):
    pass


class TestRegisterDecorator:
    def setup_method(self):
        """Clear registry before each test"""
        component_registry.clear()

    def test_register_without_arguments(self):
        """Test @register decorator without arguments"""

        @register
        class TestPublisher(MockPublisher):
            pass

        # Should add class attribute
        assert TestPublisher._auto_start is True

        # Should register with component registry
        all_regs = component_registry.get_all_registrations()
        assert len(all_regs['publishers']) == 1

        pub_reg = all_regs['publishers'][0]
        assert pub_reg['class_'] == TestPublisher
        assert pub_reg['constructor_kwargs'] == {}
        assert pub_reg['auto_start'] is True

    def test_register_with_constructor_kwargs(self):
        """Test @register with constructor arguments"""

        @register(config="test_config", timeout=30)
        class TestSubscriber(MockSubscriber):
            pass

        assert TestSubscriber._auto_start is True

        all_regs = component_registry.get_all_registrations()
        assert len(all_regs['subscribers']) == 1

        sub_reg = all_regs['subscribers'][0]
        assert sub_reg['class_'] == TestSubscriber
        assert sub_reg['constructor_kwargs'] == {'config': 'test_config', 'timeout': 30}

    def test_register_with_auto_start_false(self):
        """Test @register with auto_start=False"""

        @register(auto_start=False, param="value")
        class TestTransceiver(MockTransceiver):
            pass

        assert TestTransceiver._auto_start is False

        all_regs = component_registry.get_all_registrations()
        assert len(all_regs['transceivers']) == 1

        trans_reg = all_regs['transceivers'][0]
        assert trans_reg['auto_start'] is False
        assert trans_reg['constructor_kwargs'] == {'param': 'value'}

    def test_register_syntax_variations(self):
        """Test different decorator syntax variations work"""

        # @register
        @register
        class TestClass1(MockPublisher):
            pass

        # @register()
        @register()
        class TestClass2(MockPublisher):
            pass

        # @register(param=value)
        @register(param="value")
        class TestClass3(MockPublisher):
            pass

        # All should have _auto_start attribute
        assert TestClass1._auto_start is True
        assert TestClass2._auto_start is True
        assert TestClass3._auto_start is True

        # All should be registered
        all_regs = component_registry.get_all_registrations()
        assert len(all_regs['publishers']) == 3

    def test_component_type_detection(self):
        """Test that different component types are registered correctly"""

        @register
        class TestPub(MockPublisher):
            pass

        @register
        class TestSub(MockSubscriber):
            pass

        @register
        class TestTrans(MockTransceiver):
            pass

        all_regs = component_registry.get_all_registrations()

        # Should be in correct categories
        assert len(all_regs['publishers']) == 1
        assert len(all_regs['subscribers']) == 1
        assert len(all_regs['transceivers']) == 1

        # Check class types
        assert all_regs['publishers'][0]['class_'] == TestPub
        assert all_regs['subscribers'][0]['class_'] == TestSub
        assert all_regs['transceivers'][0]['class_'] == TestTrans

    def test_register_preserves_class_functionality(self):
        """Test that decorator doesn't break the class"""

        @register(param="test")
        class TestClass(MockPublisher):
            class_var = "test_value"

            def custom_method(self):
                return "custom_result"

        # Class should work normally
        assert TestClass.class_var == "test_value"

        instance = TestClass()
        assert instance.custom_method() == "custom_result"
        assert instance.param1 is None  # From MockPublisher.__init__

        # Should have decorator attribute
        assert TestClass._auto_start is True

    def test_invalid_component_type_raises_error(self):
        """Test that invalid component types raise error"""

        class InvalidClass:
            pass

        with pytest.raises(ValueError, match="must inherit from Publisher, Subscriber"):
            @register
            class BadClass(InvalidClass):
                pass
