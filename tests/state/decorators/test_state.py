import pytest
import asyncio
from unittest.mock import Mock
from events import state


class MockStateMachine:
    def __init__(self):
        self._current_state = "idle"


class TestStateDecorator:
    @pytest.mark.asyncio
    async def test_basic_decorator_functionality(self):
        """Test basic state decorator attributes and behavior"""

        @state("test_state", poll_interval=0.5)
        async def test_method(self, event=None):
            return "next_state"

        # Check decorator sets attributes correctly
        assert test_method._is_state is True
        assert test_method._state_name == "test_state"
        assert test_method._default_poll_interval == 0.5

        # Check method still works
        mock_self = MockStateMachine()
        result = await test_method(mock_self)
        assert result == "next_state"

    @pytest.mark.asyncio
    async def test_default_poll_interval(self):
        """Test decorator uses default poll interval when not specified"""

        @state("test_state")
        async def test_method(self, event=None):
            return None

        assert test_method._default_poll_interval == 0.1

    @pytest.mark.asyncio
    async def test_polling_when_no_transition(self):
        """Test that method polls when returning None (no transition)"""
        mock_self = MockStateMachine()

        @state("test_state", poll_interval=0.01)  # Very short for testing
        async def test_method(self, event=None):
            return None

        start_time = asyncio.get_event_loop().time()
        result = await test_method(mock_self)
        end_time = asyncio.get_event_loop().time()

        assert result is None
        assert end_time - start_time >= 0.01  # Should have slept

    @pytest.mark.asyncio
    async def test_polling_when_same_state(self):
        """Test that method polls when returning current state"""
        mock_self = MockStateMachine()
        mock_self._current_state = "idle"

        @state("idle", poll_interval=0.01)
        async def test_method(self, event=None):
            return "idle"  # Same as current state

        start_time = asyncio.get_event_loop().time()
        result = await test_method(mock_self)
        end_time = asyncio.get_event_loop().time()

        assert result == "idle"
        assert end_time - start_time >= 0.01  # Should have slept

    @pytest.mark.asyncio
    async def test_no_polling_on_transition(self):
        """Test that method doesn't poll when transitioning to different state"""
        mock_self = MockStateMachine()
        mock_self._current_state = "idle"

        @state("idle", poll_interval=0.1)
        async def test_method(self, event=None):
            return "active"  # Different from current state

        start_time = asyncio.get_event_loop().time()
        result = await test_method(mock_self)
        end_time = asyncio.get_event_loop().time()

        assert result == "active"
        # Should not poll since it's transitioning
        assert end_time - start_time < 0.05

    @pytest.mark.asyncio
    async def test_runtime_poll_interval_override(self):
        """Test that runtime poll interval overrides decorator default"""
        mock_self = MockStateMachine()
        mock_self._test_state_poll_interval = 0.02  # Runtime override

        @state("test_state", poll_interval=0.1)  # Default interval
        async def test_method(self, event=None):
            return None

        start_time = asyncio.get_event_loop().time()
        await test_method(mock_self)
        end_time = asyncio.get_event_loop().time()

        # Should use runtime interval (0.02) not default (0.1)
        assert 0.02 <= end_time - start_time < 0.05

    @pytest.mark.asyncio
    async def test_method_with_event_parameter(self):
        """Test that event parameter is passed through correctly"""
        mock_self = MockStateMachine()
        mock_event = Mock()

        @state("test_state")
        async def test_method(self, event=None):
            return event

        result = await test_method(mock_self, mock_event)
        assert result is mock_event

    @pytest.mark.asyncio
    async def test_exception_propagation(self):
        """Test that exceptions in state methods are propagated"""
        mock_self = MockStateMachine()

        @state("test_state")
        async def failing_method(self, event=None):
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            await failing_method(mock_self)

    @pytest.mark.asyncio
    async def test_preserves_method_behavior(self):
        """Test that decorator preserves original method behavior"""
        call_count = 0

        @state("test_state")
        async def test_method(self, event=None, custom_param="default"):
            nonlocal call_count
            call_count += 1
            return f"called_with_{custom_param}"

        mock_self = MockStateMachine()
        result = await test_method(mock_self, None, "custom")

        assert result == "called_with_custom"
        assert call_count == 1

    def test_multiple_decorated_methods(self):
        """Test that multiple methods can be decorated independently"""

        class TestClass:
            @state("state1", poll_interval=0.1)
            async def method1(self, event=None):
                return None

            @state("state2", poll_interval=0.2)
            async def method2(self, event=None):
                return None

        instance = TestClass()

        assert instance.method1._state_name == "state1"
        assert instance.method1._default_poll_interval == 0.1
        assert instance.method2._state_name == "state2"
        assert instance.method2._default_poll_interval == 0.2
