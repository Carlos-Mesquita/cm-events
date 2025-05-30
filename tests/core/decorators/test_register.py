from events.core.decorators._register import _register_single_instance
from events import component_registry


class TestClass:
    pass


class TestRegisterSingleInstance:
    def setup_method(self):
        """Clear registry before each test"""
        component_registry.clear()

    def test_basic_registration(self):
        """Test basic component registration"""
        _register_single_instance(
            class_=TestClass,
            constructor_kwargs={"param1": "value1"},
            auto_start=True,
            component_type="publishers"
        )

        # Verify it was actually registered
        all_regs = component_registry.get_all_registrations()
        assert len(all_regs['publishers']) == 1

        registration = all_regs['publishers'][0]
        assert registration['class_'] == TestClass
        assert registration['constructor_kwargs'] == {"param1": "value1"}
        assert registration['auto_start'] is True
        assert registration['component_id'] == "TestClass"

    def test_registration_with_custom_id(self):
        """Test registration with custom component ID"""
        _register_single_instance(
            class_=TestClass,
            constructor_kwargs={},
            auto_start=False,
            component_type="subscribers",
            id_="custom_id"
        )

        all_regs = component_registry.get_all_registrations()
        registration = all_regs['subscribers'][0]
        assert registration['component_id'] == "custom_id"
        assert registration['auto_start'] is False

    def test_registration_with_index(self):
        """Test registration with index for multiple instances"""
        _register_single_instance(
            class_=TestClass,
            constructor_kwargs={},
            auto_start=True,
            component_type="transceivers",
            index=2
        )

        all_regs = component_registry.get_all_registrations()
        registration = all_regs['transceivers'][0]
        assert registration['component_id'] == "TestClass_2"

    def test_registration_with_custom_id_and_index(self):
        """Test registration with both custom ID and index"""
        _register_single_instance(
            class_=TestClass,
            constructor_kwargs={},
            auto_start=True,
            component_type="publishers",
            index=5,
            id_="custom"
        )

        all_regs = component_registry.get_all_registrations()
        registration = all_regs['publishers'][0]
        assert registration['component_id'] == "custom_5"
