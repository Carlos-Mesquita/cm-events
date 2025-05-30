import pytest
from pydantic import ValidationError
from events import ComponentRegistration


class MockComponent:
    pass


class TestComponentRegistration:
    def test_basic_creation_with_defaults(self):
        """Test creation with required fields and default values"""
        registration = ComponentRegistration(
            **{"class": MockComponent, "component_id": "test_component"}
        )

        assert registration.class_ == MockComponent
        assert registration.component_id == "test_component"
        assert registration.constructor_kwargs == {}
        assert registration.auto_start is True

    def test_creation_with_all_fields(self):
        """Test creation with all fields specified"""
        kwargs = {"param1": "value1", "param2": 42}

        registration = ComponentRegistration(**{
            "class": MockComponent,
            "constructor_kwargs": kwargs,
            "auto_start": False,
            "component_id": "custom_id"
        })

        assert registration.class_ == MockComponent
        assert registration.constructor_kwargs == kwargs
        assert registration.auto_start is False
        assert registration.component_id == "custom_id"

    def test_required_fields_validation(self):
        """Test that required fields are properly validated"""
        # No fields at all
        with pytest.raises(ValidationError):
            ComponentRegistration()

        # Missing component_id
        with pytest.raises(ValidationError):
            ComponentRegistration(**{"class": MockComponent})

        # Missing class
        with pytest.raises(ValidationError):
            ComponentRegistration(component_id="test")

    def test_model_serialization(self):
        """Test model_dump() serialization"""
        registration = ComponentRegistration(**{
            "class": MockComponent,
            "constructor_kwargs": {"param": "value"},
            "auto_start": False,
            "component_id": "dump_test"
        })

        dumped = registration.model_dump()

        # Verify all fields are present and correct
        assert dumped["class_"] == MockComponent
        assert dumped["constructor_kwargs"] == {"param": "value"}
        assert dumped["auto_start"] is False
        assert dumped["component_id"] == "dump_test"

        # Verify it contains all expected keys
        expected_keys = {"class_", "constructor_kwargs", "auto_start", "component_id"}
        assert set(dumped.keys()) == expected_keys
