import pytest
import asyncio
import time
from unittest.mock import Mock

import pytest_asyncio

from events import StateMachine, Event, EventType, initial_state, state


class MockEvents(EventType):
    STATE_CHANGED = "state_changed"
    TEST_EVENT = "test_event"


@pytest_asyncio.fixture
async def cleanup_tasks():
    """Cleanup any remaining asyncio tasks after each test"""
    yield
    # Cancel any remaining tasks
    tasks = [t for t in asyncio.all_tasks() if not t.done()]
    for task in tasks:
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass


class TestStateMachine:
    def test_initialization(self):
        """Test basic state machine setup"""
        sm = StateMachine()

        assert sm._current_state is None
        assert sm._previous_state is None
        assert sm._state_machine_running is False
        assert sm._consecutive_errors == 0
        assert sm._max_consecutive_errors == 5

    def test_initialization_with_params(self):
        """Test initialization with custom parameters"""
        sm = StateMachine(
            state_change_event_type=MockEvents.STATE_CHANGED,
            max_consecutive_errors=3
        )

        assert sm._max_consecutive_errors == 3
        assert sm._state_change_event_type == MockEvents.STATE_CHANGED

    def test_transition_validation_no_map(self):
        """Test transitions when no map is defined"""
        sm = StateMachine()

        # No transition map means all transitions are valid
        assert sm._is_valid_transition("any", "state") is True

    def test_transition_validation_with_map(self):
        """Test transition validation with defined map"""

        class TestSM(StateMachine):
            _transition_map = {"idle": {"active", "error"}, "active": {"idle"}}

        sm = TestSM()

        assert sm._is_valid_transition("idle", "active") is True
        assert sm._is_valid_transition("idle", "error") is True
        assert sm._is_valid_transition("active", "idle") is True
        assert sm._is_valid_transition("idle", "unknown") is False
        assert sm._is_valid_transition("active", "error") is False

    @pytest.mark.asyncio
    async def test_transition_to_unknown_state(self, caplog):
        """Test transitioning to non-existent state"""
        sm = StateMachine()

        result = await sm.transition_to("unknown")

        assert result is False
        assert "Unknown state: unknown" in caplog.text

    @pytest.mark.asyncio
    async def test_transition_to_invalid_transition(self, caplog):
        """Test invalid state transition"""

        class TestSM(StateMachine):
            _transition_map = {"idle": {"active"}}

        sm = TestSM()
        sm._current_state = "idle"
        sm._state_handlers = {"idle": Mock(), "error": Mock()}

        result = await sm.transition_to("error")

        assert result is False
        assert "Invalid transition" in caplog.text

    @pytest.mark.asyncio
    async def test_successful_transition(self):
        """Test successful state transition"""
        sm = StateMachine()
        sm._state_handlers = {"active": Mock()}

        result = await sm.transition_to("active")

        assert result is True
        assert sm._current_state == "active"
        assert sm._previous_state is None
        assert sm._state_start_time > 0

    @pytest.mark.asyncio
    async def test_state_change_event_publishing(self):
        """Test that state changes publish events when configured"""
        published_events = []

        class TestSM(StateMachine):
            def __init__(self):
                super().__init__(state_change_event_type=MockEvents.STATE_CHANGED)

            async def publish(self, event):
                published_events.append(event)

        sm = TestSM()
        sm._state_handlers = {"active": Mock()}

        await sm.transition_to("active")

        assert len(published_events) == 1
        event = published_events[0]
        assert event.type == MockEvents.STATE_CHANGED
        assert event.payload["current_state"] == "active"
        assert event.payload["previous_state"] is None

    @pytest.mark.asyncio
    async def test_start_no_initial_state(self, caplog):
        """Test starting without initial state"""
        sm = StateMachine()

        result = await sm.start()

        assert result is False
        assert "No initial state defined" in caplog.text

    @pytest.mark.asyncio
    async def test_start_already_running(self, caplog, cleanup_tasks):
        """Test attempting to start already running machine"""

        @initial_state("idle")
        class TestSM(StateMachine):
            @state("idle")
            async def idle_state(self):
                return False  # Stop immediately

        sm = TestSM()

        try:
            await asyncio.wait_for(sm.start(), timeout=2.0)
            result = await sm.start()  # Try to start again

            assert result is False
            assert "already running" in caplog.text
        finally:
            await sm.stop()

    @pytest.mark.asyncio
    async def test_stop_state_machine(self, cleanup_tasks):
        """Test stopping a running state machine"""

        @initial_state("idle")
        class TestSM(StateMachine):
            @state("idle", poll_interval=0.1)
            async def idle_state(self):
                return None  # Keep running

        sm = TestSM()

        try:
            await asyncio.wait_for(sm.start(), timeout=2.0)
            await asyncio.sleep(0.05)  # Let it start

            assert sm.is_running is True

            await sm.stop()
            assert sm.is_running is False
            assert sm._state_machine_running is False
        finally:
            if sm.is_running:
                await sm.stop()

    @pytest.mark.asyncio
    async def test_restart_resets_error_count(self, cleanup_tasks):
        """Test that restart resets consecutive error count"""

        @initial_state("idle")
        class TestSM(StateMachine):
            @state("idle")
            async def idle_state(self):
                return False  # Stop immediately

        sm = TestSM()
        sm._consecutive_errors = 3

        try:
            await asyncio.wait_for(sm.restart(), timeout=2.0)
            assert sm._consecutive_errors == 0
        finally:
            await sm.stop()

    @pytest.mark.asyncio
    async def test_consecutive_error_handling(self, caplog):
        """Test consecutive error limit and recovery"""

        class TestSM(StateMachine):
            def __init__(self):
                super().__init__(max_consecutive_errors=2)
                self.error_count = 0

            async def failing_state(self):
                self.error_count += 1
                raise Exception(f"Error {self.error_count}")

        sm = TestSM()
        sm._current_state = "failing"
        sm._state_handlers = {"failing": sm.failing_state}

        await asyncio.wait_for(sm._run_state_machine(), timeout=2.0)

        # Should stop after hitting error limit
        assert sm.error_count >= 1
        assert "State machine error" in caplog.text

    @pytest.mark.asyncio
    async def test_error_state_recovery(self):
        """Test recovery using error state"""

        class TestSM(StateMachine):
            def __init__(self):
                super().__init__()
                self.error_state_called = False
                self.test_calls = 0

            async def failing_state(self):
                self.test_calls += 1
                if self.test_calls == 1:
                    raise Exception("Test error")
                return False  # Stop on second call

            async def error_state(self):
                self.error_state_called = True
                return "failing"  # Try again

        sm = TestSM()
        sm._current_state = "failing"
        sm._state_handlers = {
            "failing": sm.failing_state,
            "error": sm.error_state
        }

        await asyncio.wait_for(sm._run_state_machine(), timeout=2.0)

        assert sm.error_state_called is True
        assert sm.test_calls == 2  # Should have tried twice

    def test_poll_interval_management(self):
        """Test setting and getting poll intervals"""
        sm = StateMachine()

        # Test setting runtime interval
        sm.set_poll_interval("test_state", 0.5)
        assert sm.get_poll_interval("test_state") == 0.5

        # Test fallback interval
        assert sm.get_poll_interval("unknown_state") == 0.1

    def test_poll_interval_from_decorator(self):
        """Test getting poll interval from decorated method"""
        sm = StateMachine()

        # Mock a handler with default poll interval
        handler = Mock()
        handler._default_poll_interval = 0.7
        sm._state_handlers = {"test_state": handler}

        assert sm.get_poll_interval("test_state") == 0.7

    def test_properties(self):
        """Test state machine properties"""
        sm = StateMachine()
        sm._current_state = "test_state"
        sm._previous_state = "old_state"
        sm._state_start_time = time.monotonic() - 1.0
        sm._state_handlers = {"test": Mock(), "another": Mock()}

        assert sm.current_state == "test_state"
        assert sm.previous_state == "old_state"
        assert sm.state_uptime >= 1.0
        assert sm.available_states == {"test", "another"}

    def test_state_uptime_no_current_state(self):
        """Test uptime when no current state"""
        sm = StateMachine()
        assert sm.state_uptime == 0.0

    def test_is_running_property(self):
        """Test is_running property logic"""
        sm = StateMachine()

        # Not running initially
        assert sm.is_running is False

        # Mock running state
        sm._state_machine_running = True
        sm._state_task = Mock()
        sm._state_task.done.return_value = False
        assert sm.is_running is True

        # Task done
        sm._state_task.done.return_value = True
        assert sm.is_running is False

    @pytest.mark.asyncio
    async def test_decorator_integration(self, cleanup_tasks):
        """Test real decorator usage"""

        @initial_state("start")
        class RealSM(StateMachine):
            def __init__(self):
                super().__init__()
                self.states_visited = []

            @state("start")
            async def start_state(self):
                self.states_visited.append("start")
                return "middle"

            @state("middle")
            async def middle_state(self):
                self.states_visited.append("middle")
                return False  # Stop

        sm = RealSM()

        try:
            await asyncio.wait_for(sm.start(), timeout=2.0)
            await asyncio.sleep(0.1)  # Let it run

            assert "start" in sm.states_visited
            assert sm._initial_state == "start"
            assert "start" in sm._state_handlers
            assert "middle" in sm._state_handlers
        finally:
            await sm.stop()

    @pytest.mark.asyncio
    async def test_event_handling_integration(self):
        """Test state machine with event handling"""

        class EventAwareSM(StateMachine):
            def __init__(self):
                super().__init__()
                self.received_events = []
                # Simulate having handle_event method (like a Subscriber)

            async def handle_event(self, event):
                self.received_events.append(event)

        sm = EventAwareSM()

        # Verify monkey patching happened
        assert hasattr(sm, '_original_handle_event')
        assert sm.handle_event != sm._original_handle_event

        event = Event(type=MockEvents.TEST_EVENT, source="test", payload={})

        await sm._state_aware_handle_event(event)

        assert sm._current_event == event
        assert len(sm.received_events) == 1

    @pytest.mark.asyncio
    async def test_state_handler_with_event(self):
        """Test state handler receiving current event"""

        class TestSM(StateMachine):
            def __init__(self):
                super().__init__()
                self.received_event = None

            async def test_state(self, event=None):
                self.received_event = event
                return False  # Stop immediately

        sm = TestSM()
        sm._current_state = "test_state"
        sm._state_handlers = {"test_state": sm.test_state}

        # Set a current event
        test_event = Event(type=MockEvents.TEST_EVENT, source="test", payload={"data": "test"})
        sm._current_event = test_event

        await asyncio.wait_for(sm._run_state_machine(), timeout=2.0)

        # Should have received the event and cleared it
        assert sm.received_event == test_event
        assert sm._current_event is None

    @pytest.mark.asyncio
    async def test_max_consecutive_errors_reached(self, caplog):
        """Test stopping when max consecutive errors is reached"""

        class TestSM(StateMachine):
            def __init__(self):
                super().__init__(max_consecutive_errors=2)
                self.error_count = 0

            async def failing_state(self):
                self.error_count += 1
                raise Exception(f"Error {self.error_count}")

            async def error_state(self):
                # Error state that also fails to handle errors
                raise Exception("Error state also fails")

        sm = TestSM()
        sm._current_state = "failing"
        sm._state_handlers = {
            "failing": sm.failing_state,
            "error": sm.error_state  # Add error state so it keeps trying
        }

        await asyncio.wait_for(sm._run_state_machine(), timeout=2.0)

        # Should have hit the consecutive error limit
        assert sm._consecutive_errors >= 2
        assert "Too many consecutive errors, stopping state machine" in caplog.text
