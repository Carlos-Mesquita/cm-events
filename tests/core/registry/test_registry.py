import pytest
from events.core.registry import ComponentRegistry, ComponentRegistration, component_registry


class MockPublisher:
    pass


class MockSubscriber:
    pass


class MockTransceiver:
    pass


class TestComponentRegistry:
    def test_initialization(self):
        """Test registry initializes empty"""
        registry = ComponentRegistry()

        assert registry.publishers == []
        assert registry.subscribers == []
        assert registry.transceivers == []
        assert registry.total_count == 0

    def test_add_registration_all_types(self):
        """Test adding registrations for all component types"""
        registry = ComponentRegistry()

        pub_reg = ComponentRegistration(**{"class": MockPublisher, "component_id": "pub1"})
        sub_reg = ComponentRegistration(**{"class": MockSubscriber, "component_id": "sub1"})
        trans_reg = ComponentRegistration(**{"class": MockTransceiver, "component_id": "trans1"})

        registry.add_registration("publishers", pub_reg)
        registry.add_registration("subscribers", sub_reg)
        registry.add_registration("transceivers", trans_reg)

        assert len(registry.publishers) == 1
        assert len(registry.subscribers) == 1
        assert len(registry.transceivers) == 1
        assert registry.total_count == 3

    def test_add_invalid_component_type(self):
        """Test adding registration with invalid component type raises error"""
        registry = ComponentRegistry()
        registration = ComponentRegistration(**{"class": MockPublisher, "component_id": "test"})

        with pytest.raises(ValueError, match="Unknown component type: invalid_type"):
            registry.add_registration("invalid_type", registration)

    def test_get_all_registrations_format(self):
        """Test get_all_registrations returns correct format"""
        registry = ComponentRegistry()

        # Test empty case
        all_regs = registry.get_all_registrations()
        expected_empty = {'publishers': [], 'subscribers': [], 'transceivers': []}
        assert all_regs == expected_empty

        # Test with data
        pub_reg = ComponentRegistration(**{
            "class": MockPublisher,
            "component_id": "pub1",
            "constructor_kwargs": {"param": "value"},
            "auto_start": False
        })
        registry.add_registration("publishers", pub_reg)

        all_regs = registry.get_all_registrations()

        assert len(all_regs['publishers']) == 1
        assert len(all_regs['subscribers']) == 0
        assert len(all_regs['transceivers']) == 0

        # Verify model_dump() format
        pub_data = all_regs['publishers'][0]
        assert pub_data['class_'] == MockPublisher
        assert pub_data['component_id'] == "pub1"
        assert pub_data['constructor_kwargs'] == {"param": "value"}
        assert pub_data['auto_start'] is False

    def test_clear_functionality(self):
        """Test clear removes all registrations"""
        registry = ComponentRegistry()

        # Add some registrations
        registry.add_registration("publishers",
                                  ComponentRegistration(**{"class": MockPublisher, "component_id": "pub1"}))
        registry.add_registration("subscribers",
                                  ComponentRegistration(**{"class": MockSubscriber, "component_id": "sub1"}))

        assert registry.total_count == 2

        registry.clear()

        assert registry.total_count == 0
        assert len(registry.publishers) == 0
        assert len(registry.subscribers) == 0
        assert len(registry.transceivers) == 0

    def test_multiple_registrations_same_type(self):
        """Test adding multiple registrations of same type"""
        registry = ComponentRegistry()

        for i in range(3):
            registry.add_registration("publishers", ComponentRegistration(
                **{"class": MockPublisher, "component_id": f"pub{i}"}
            ))

        assert len(registry.publishers) == 3
        assert registry.total_count == 3

        # Verify all have unique IDs
        ids = [reg.component_id for reg in registry.publishers]
        assert len(set(ids)) == 3
        assert ids == ["pub0", "pub1", "pub2"]


class TestGlobalComponentRegistry:
    def test_global_registry_exists_and_singleton(self):
        """Test global registry exists and is singleton"""
        # Test existence
        assert component_registry is not None
        assert isinstance(component_registry, ComponentRegistry)

        # Test singleton behavior
        from events.core.registry import component_registry as registry2
        assert component_registry is registry2

    def test_global_registry_functionality(self):
        """Test global registry basic functionality"""
        # Clean slate
        component_registry.clear()
        initial_count = component_registry.total_count

        registration = ComponentRegistration(**{
            "class": MockPublisher,
            "component_id": "global_test"
        })

        component_registry.add_registration("publishers", registration)

        assert component_registry.total_count == initial_count + 1
        assert any(reg.component_id == "global_test" for reg in component_registry.publishers)

        # Clean up
        component_registry.clear()