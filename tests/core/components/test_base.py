import pytest
from unittest.mock import Mock
from events.core.components._base import Base


class TestBase:
    def test_init_with_broker(self):
        mock_broker = Mock()
        base = Base(broker=mock_broker)
        assert base._broker is mock_broker
        assert base._logger is not None

    def test_init_without_broker(self):
        base = Base()
        assert base._broker is None
        assert base._logger is not None

    def test_logger_uses_class_module(self):
        base = Base()
        expected_module = base.__class__.__module__
        assert base._logger.name == expected_module

    @pytest.mark.asyncio
    async def test_startup_default_implementation(self):
        base = Base()
        # Should not raise - default implementation does nothing
        await base.startup()

    @pytest.mark.asyncio
    async def test_shutdown_default_implementation(self):
        base = Base()
        # Should not raise - default implementation does nothing
        await base.shutdown()

    def test_broker_can_be_none(self):
        base = Base(broker=None)
        assert base._broker is None

    def test_broker_assignment(self):
        mock_broker = Mock()
        base = Base()
        assert base._broker is None

        base._broker = mock_broker
        assert base._broker is mock_broker
