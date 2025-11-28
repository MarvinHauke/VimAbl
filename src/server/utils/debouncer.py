"""
Debouncing utilities for high-frequency events.

This module provides debouncing functionality to reduce the rate of
event processing and broadcasting for rapidly changing values like
device parameters and tempo.
"""

import asyncio
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass
import time
import logging

from ..constants import EventConstants

logger = logging.getLogger(__name__)


@dataclass
class DebouncedEvent:
    """
    Container for a debounced event.

    Attributes:
        event_type: Type of event
        event_args: Event arguments
        timestamp: Time when event was first received
        last_update: Time of most recent update
        pending_task: Optional asyncio task for delayed execution
    """
    event_type: str
    event_args: Dict[str, Any]
    timestamp: float
    last_update: float
    pending_task: Optional[asyncio.Task] = None


class DebouncedBroadcaster:
    """
    Manages debouncing for high-frequency events.

    This class collects rapid events and broadcasts them only after
    a quiet period, reducing network traffic and UI update overhead.

    Usage:
        debouncer = DebouncedBroadcaster(delay=0.1)

        # Add events (will be debounced)
        await debouncer.debounce("tempo_changed", {"tempo": 120.5}, handler)
        await debouncer.debounce("tempo_changed", {"tempo": 121.0}, handler)

        # Only the last value (121.0) will be processed after delay
    """

    def __init__(self, delay: float = EventConstants.DEBOUNCE_DELAY_SECONDS):
        """
        Initialize debouncer.

        Args:
            delay: Debounce delay in seconds (default from EventConstants)
        """
        self.delay = delay
        self.pending_events: Dict[str, DebouncedEvent] = {}
        self.logger = logging.getLogger(f"{__name__}.DebouncedBroadcaster")

    def _create_event_key(self, event_type: str, event_args: Dict[str, Any]) -> str:
        """
        Create a unique key for the event based on type and identifying args.

        For example:
        - device_parameter_changed: "device_param_0_1_5" (track, device, param indices)
        - tempo_changed: "tempo"
        - volume_changed: "volume_0" (track index)

        Args:
            event_type: Type of event
            event_args: Event arguments

        Returns:
            Unique key string
        """
        if event_type == "device_parameter_changed":
            track = event_args.get("track_index", "?")
            device = event_args.get("device_index", "?")
            param = event_args.get("parameter_index", "?")
            return f"device_param_{track}_{device}_{param}"

        elif event_type == "tempo_changed":
            return "tempo"

        elif event_type == "volume_changed":
            track = event_args.get("track_index", "?")
            return f"volume_{track}"

        elif event_type == "pan_changed":
            track = event_args.get("track_index", "?")
            return f"pan_{track}"

        else:
            # Default: just use event type (all instances share same key)
            return event_type

    async def debounce(
        self,
        event_type: str,
        event_args: Dict[str, Any],
        handler: Callable,
        immediate: bool = False
    ) -> None:
        """
        Debounce an event.

        Args:
            event_type: Type of event
            event_args: Event arguments
            handler: Async function to call with (event_type, event_args)
            immediate: If True, execute immediately (bypass debouncing)
        """
        if immediate:
            await handler(event_type, event_args)
            return

        event_key = self._create_event_key(event_type, event_args)
        current_time = time.time()

        # Cancel existing pending task if any
        if event_key in self.pending_events:
            existing = self.pending_events[event_key]
            if existing.pending_task and not existing.pending_task.done():
                existing.pending_task.cancel()

        # Create new debounced event
        debounced = DebouncedEvent(
            event_type=event_type,
            event_args=event_args,
            timestamp=current_time,
            last_update=current_time
        )

        # Schedule delayed execution
        debounced.pending_task = asyncio.create_task(
            self._execute_after_delay(event_key, handler)
        )

        self.pending_events[event_key] = debounced

    async def _execute_after_delay(self, event_key: str, handler: Callable) -> None:
        """
        Execute handler after delay period.

        Args:
            event_key: Key of the event
            handler: Handler to execute
        """
        try:
            await asyncio.sleep(self.delay)

            # Retrieve event (it might have been updated)
            if event_key in self.pending_events:
                event = self.pending_events[event_key]

                self.logger.debug(
                    f"Executing debounced event {event.event_type} "
                    f"(age: {time.time() - event.timestamp:.3f}s)"
                )

                # Execute handler
                await handler(event.event_type, event.event_args)

                # Clean up
                del self.pending_events[event_key]

        except asyncio.CancelledError:
            # Task was cancelled because a new event arrived
            self.logger.debug(f"Debounced event {event_key} was cancelled (updated)")
            pass
        except Exception as e:
            self.logger.exception(f"Error executing debounced event {event_key}: {e}")
            # Clean up on error
            if event_key in self.pending_events:
                del self.pending_events[event_key]

    async def flush(self, event_key: str = None) -> None:
        """
        Immediately execute pending events without waiting for delay.

        Args:
            event_key: Optional specific event key to flush. If None, flushes all.
        """
        if event_key:
            if event_key in self.pending_events:
                event = self.pending_events[event_key]
                if event.pending_task and not event.pending_task.done():
                    event.pending_task.cancel()
                del self.pending_events[event_key]
        else:
            # Flush all
            for key in list(self.pending_events.keys()):
                event = self.pending_events[key]
                if event.pending_task and not event.pending_task.done():
                    event.pending_task.cancel()
            self.pending_events.clear()

    def get_pending_count(self) -> int:
        """Get count of pending debounced events."""
        return len(self.pending_events)

    def is_pending(self, event_type: str, event_args: Dict[str, Any]) -> bool:
        """
        Check if an event is currently pending.

        Args:
            event_type: Type of event
            event_args: Event arguments

        Returns:
            True if event is pending
        """
        event_key = self._create_event_key(event_type, event_args)
        return event_key in self.pending_events


class EventRateLimiter:
    """
    Simple rate limiter for events using a sliding window.

    This is useful when you want to limit the rate of events but
    still process all of them (unlike debouncing which only keeps the last).

    Usage:
        limiter = EventRateLimiter(max_per_second=10)

        if limiter.should_process("device_param_0_1_5"):
            await process_event(...)
    """

    def __init__(self, max_per_second: float = 10.0):
        """
        Initialize rate limiter.

        Args:
            max_per_second: Maximum events per second per key
        """
        self.max_per_second = max_per_second
        self.min_interval = 1.0 / max_per_second
        self.last_times: Dict[str, float] = {}

    def should_process(self, event_key: str) -> bool:
        """
        Check if event should be processed based on rate limit.

        Args:
            event_key: Unique key for the event

        Returns:
            True if event should be processed
        """
        current_time = time.time()
        last_time = self.last_times.get(event_key, 0)

        if current_time - last_time >= self.min_interval:
            self.last_times[event_key] = current_time
            return True

        return False

    def reset(self, event_key: str = None) -> None:
        """
        Reset rate limiter for a specific key or all keys.

        Args:
            event_key: Optional specific key to reset. If None, resets all.
        """
        if event_key:
            self.last_times.pop(event_key, None)
        else:
            self.last_times.clear()
