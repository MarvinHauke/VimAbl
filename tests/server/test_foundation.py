"""
Tests for the refactored foundation infrastructure.

Tests the new handlers, validation, and utilities modules.
"""

import pytest
import asyncio
from src.server.handlers import EventResult, validate_args, handle_exceptions
from src.server.validation import (
    validate_event_args,
    validate_required_keys,
    validate_type,
    validate_range,
    validate_index,
    safe_get,
)
from src.server.utils import DebouncedBroadcaster


class TestEventResult:
    """Test EventResult dataclass."""

    def test_ok_result(self):
        """Test creating a successful result."""
        result = EventResult.ok(diff={"changes": []}, track_idx=0)
        assert result.success is True
        assert result.diff == {"changes": []}
        assert result.metadata == {"track_idx": 0}
        assert result.error_message is None

    def test_error_result(self):
        """Test creating an error result."""
        result = EventResult.error("Something went wrong", error_type="test_error")
        assert result.success is False
        assert result.error_message == "Something went wrong"
        assert result.error_type == "test_error"
        assert result.diff is None

    def test_builder_pattern(self):
        """Test builder pattern methods."""
        result = EventResult.ok()
        result.with_diff({"changes": []}).with_metadata(track_idx=0, scene_idx=1)

        assert result.diff == {"changes": []}
        assert result.metadata == {"track_idx": 0, "scene_idx": 1}


class TestValidators:
    """Test validation functions."""

    def test_validate_required_keys_success(self):
        """Test successful validation of required keys."""
        args = {"track_index": 0, "device_index": 1}
        valid, error = validate_required_keys(args, "track_index", "device_index")
        assert valid is True
        assert error is None

    def test_validate_required_keys_missing(self):
        """Test validation failure with missing keys."""
        args = {"track_index": 0}
        valid, error = validate_required_keys(args, "track_index", "device_index")
        assert valid is False
        assert "device_index" in error

    def test_validate_type_success(self):
        """Test successful type validation."""
        valid, error = validate_type(42, int, "track_index")
        assert valid is True
        assert error is None

    def test_validate_type_failure(self):
        """Test type validation failure."""
        valid, error = validate_type("42", int, "track_index")
        assert valid is False
        assert "track_index" in error

    def test_validate_range_success(self):
        """Test successful range validation."""
        valid, error = validate_range(0.5, 0.0, 1.0, "volume")
        assert valid is True
        assert error is None

    def test_validate_range_below_min(self):
        """Test range validation below minimum."""
        valid, error = validate_range(-0.1, 0.0, 1.0, "volume")
        assert valid is False
        assert "below minimum" in error

    def test_validate_range_above_max(self):
        """Test range validation above maximum."""
        valid, error = validate_range(1.1, 0.0, 1.0, "volume")
        assert valid is False
        assert "exceeds maximum" in error

    def test_validate_index_success(self):
        """Test successful index validation."""
        valid, error = validate_index(0, "track_index")
        assert valid is True
        assert error is None

    def test_validate_index_negative(self):
        """Test index validation with negative value."""
        valid, error = validate_index(-1, "track_index")
        assert valid is False

    def test_safe_get_with_default(self):
        """Test safe_get with default value."""
        args = {}
        value = safe_get(args, "device_name", "Unknown", str)
        assert value == "Unknown"

    def test_safe_get_with_value(self):
        """Test safe_get with existing value."""
        args = {"device_name": "Reverb"}
        value = safe_get(args, "device_name", "Unknown", str)
        assert value == "Reverb"

    def test_safe_get_type_mismatch(self):
        """Test safe_get with type mismatch returns default."""
        args = {"device_name": 42}  # wrong type
        value = safe_get(args, "device_name", "Unknown", str)
        assert value == "Unknown"


class TestValidateEventArgs:
    """Test validate_event_args function."""

    def test_track_added_valid(self):
        """Test valid track_added event."""
        result = validate_event_args("track_added", {"track_index": 0})
        assert result.valid is True

    def test_track_added_missing_required(self):
        """Test track_added with missing required field."""
        result = validate_event_args("track_added", {})
        assert result.valid is False
        assert "track_index" in str(result)

    def test_device_param_changed_valid(self):
        """Test valid device_parameter_changed event."""
        result = validate_event_args(
            "device_parameter_changed",
            {
                "track_index": 0,
                "device_index": 1,
                "parameter_index": 5,
                "parameter_value": 0.5,
            },
        )
        assert result.valid is True

    def test_unknown_event_type(self):
        """Test unknown event type (should pass)."""
        result = validate_event_args("unknown_event", {"foo": "bar"})
        assert result.valid is True  # No schema = pass


@pytest.mark.asyncio
class TestDebouncedBroadcaster:
    """Test DebouncedBroadcaster."""

    async def test_debounce_single_event(self):
        """Test debouncing a single event."""
        debouncer = DebouncedBroadcaster(delay=0.05)
        results = []

        async def handler(event_type, event_args):
            results.append((event_type, event_args))

        await debouncer.debounce("test_event", {"value": 1}, handler)
        await asyncio.sleep(0.1)  # Wait for debounce

        assert len(results) == 1
        assert results[0] == ("test_event", {"value": 1})

    async def test_debounce_multiple_events(self):
        """Test debouncing multiple rapid events (only last should execute)."""
        debouncer = DebouncedBroadcaster(delay=0.05)
        results = []

        async def handler(event_type, event_args):
            results.append((event_type, event_args))

        # Rapid fire events
        await debouncer.debounce("test_event", {"value": 1}, handler)
        await debouncer.debounce("test_event", {"value": 2}, handler)
        await debouncer.debounce("test_event", {"value": 3}, handler)

        await asyncio.sleep(0.1)  # Wait for debounce

        # Only the last value should have been broadcast
        assert len(results) == 1
        assert results[0] == ("test_event", {"value": 3})

    async def test_debounce_immediate(self):
        """Test immediate execution (bypass debouncing)."""
        debouncer = DebouncedBroadcaster(delay=0.1)
        results = []

        async def handler(event_type, event_args):
            results.append((event_type, event_args))

        await debouncer.debounce("test_event", {"value": 1}, handler, immediate=True)

        # Should execute immediately without waiting
        assert len(results) == 1
        assert results[0] == ("test_event", {"value": 1})

    async def test_debounce_different_keys(self):
        """Test debouncing different event keys separately."""
        debouncer = DebouncedBroadcaster(delay=0.05)
        results = []

        async def handler(event_type, event_args):
            results.append((event_type, event_args))

        # Different device parameters should debounce separately
        await debouncer.debounce(
            "device_parameter_changed",
            {"track_index": 0, "device_index": 0, "parameter_index": 0, "parameter_value": 1.0},
            handler,
        )
        await debouncer.debounce(
            "device_parameter_changed",
            {"track_index": 0, "device_index": 0, "parameter_index": 1, "parameter_value": 2.0},
            handler,
        )

        await asyncio.sleep(0.1)  # Wait for debounce

        # Both should execute (different parameters)
        assert len(results) == 2


@pytest.mark.asyncio
class TestDecorators:
    """Test decorator functions."""

    async def test_validate_args_decorator(self):
        """Test validate_args decorator."""

        class MockHandler:
            @validate_args("track_index", "device_index")
            async def handle_event(self, event_args):
                return EventResult.ok(metadata=event_args)

        handler = MockHandler()

        # Valid args
        result = await handler.handle_event({"track_index": 0, "device_index": 1})
        assert result.success is True

        # Missing args
        result = await handler.handle_event({"track_index": 0})
        assert result.success is False
        assert "device_index" in result.error_message

    async def test_handle_exceptions_decorator(self):
        """Test handle_exceptions decorator."""

        @handle_exceptions
        async def failing_handler():
            raise ValueError("Test error")

        result = await failing_handler()
        assert result.success is False
        assert "Test error" in result.error_message
        assert result.error_type == "exception"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
