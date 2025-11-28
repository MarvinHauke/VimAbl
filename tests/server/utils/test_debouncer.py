import pytest
import asyncio
import time
from src.server.utils.debouncer import DebouncedBroadcaster

@pytest.mark.asyncio
async def test_single_event_debouncing():
    """
    Test that a single event is executed after the delay.
    """
    delay = 0.05
    debouncer = DebouncedBroadcaster(delay=delay)
    
    called_args = []
    async def handler(event_type, event_args):
        called_args.append((event_type, event_args))

    await debouncer.debounce("test_event", {"val": 1}, handler)
    
    # Should not be called immediately
    assert len(called_args) == 0
    
    # Wait for delay
    await asyncio.sleep(delay + 0.02)
    
    # Should be called now
    assert len(called_args) == 1
    assert called_args[0] == ("test_event", {"val": 1})

@pytest.mark.asyncio
async def test_multiple_rapid_events_coalesce():
    """
    Test that multiple rapid events coalesce into a single execution of the last event.
    """
    delay = 0.05
    debouncer = DebouncedBroadcaster(delay=delay)
    
    called_args = []
    async def handler(event_type, event_args):
        called_args.append((event_type, event_args))

    # Send multiple events rapidly
    await debouncer.debounce("test_event", {"val": 1}, handler)
    await debouncer.debounce("test_event", {"val": 2}, handler)
    await debouncer.debounce("test_event", {"val": 3}, handler)
    
    # Should not be called yet
    assert len(called_args) == 0
    
    # Wait for delay
    await asyncio.sleep(delay + 0.02)
    
    # Should be called only once with the last value
    assert len(called_args) == 1
    assert called_args[0] == ("test_event", {"val": 3})

@pytest.mark.asyncio
async def test_immediate_mode():
    """
    Test that immediate=True bypasses debouncing.
    """
    delay = 0.05
    debouncer = DebouncedBroadcaster(delay=delay)
    
    called_args = []
    async def handler(event_type, event_args):
        called_args.append((event_type, event_args))

    await debouncer.debounce("test_event", {"val": 1}, handler, immediate=True)
    
    # Should be called immediately
    assert len(called_args) == 1
    assert called_args[0] == ("test_event", {"val": 1})
    
    # Wait to ensure no double call
    await asyncio.sleep(delay + 0.02)
    assert len(called_args) == 1

@pytest.mark.asyncio
async def test_different_keys_debounce_separately():
    """
    Test that events with different keys are debounced independently.
    """
    delay = 0.05
    debouncer = DebouncedBroadcaster(delay=delay)
    
    called_args = []
    async def handler(event_type, event_args):
        called_args.append((event_type, event_args))

    # Send events for different keys
    # volume_changed uses track_index for key generation
    await debouncer.debounce("volume_changed", {"track_index": 0, "val": 0.5}, handler)
    await debouncer.debounce("volume_changed", {"track_index": 1, "val": 0.8}, handler)
    
    # Wait for delay
    await asyncio.sleep(delay + 0.02)
    
    # Both should be called
    assert len(called_args) == 2
    # Order isn't strictly guaranteed by asyncio.sleep but usually holds.
    # We check containment.
    assert ("volume_changed", {"track_index": 0, "val": 0.5}) in called_args
    assert ("volume_changed", {"track_index": 1, "val": 0.8}) in called_args

@pytest.mark.asyncio
async def test_cleanup_of_completed_tasks():
    """
    Test that pending_events are cleaned up after execution.
    """
    delay = 0.01
    debouncer = DebouncedBroadcaster(delay=delay)
    
    async def handler(event_type, event_args):
        pass

    await debouncer.debounce("test_event", {"val": 1}, handler)
    assert debouncer.get_pending_count() == 1
    
    await asyncio.sleep(delay + 0.02)
    
    assert debouncer.get_pending_count() == 0

@pytest.mark.asyncio
async def test_flush_clears_events():
    """
    Test that flush() clears pending events.
    """
    delay = 0.1
    debouncer = DebouncedBroadcaster(delay=delay)
    
    called_args = []
    async def handler(event_type, event_args):
        called_args.append(event_args)

    await debouncer.debounce("test_event", {"val": 1}, handler)
    assert debouncer.get_pending_count() == 1
    
    await debouncer.flush()
    assert debouncer.get_pending_count() == 0
    
    # Wait to ensure handler is NOT called
    await asyncio.sleep(delay + 0.02)
    assert len(called_args) == 0
