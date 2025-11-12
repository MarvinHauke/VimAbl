#!/usr/bin/env python3
"""
Integration test for UDP/OSC communication.

Tests the complete flow:
1. Start UDP listener
2. Send test messages via UDP sender
3. Verify messages are received and parsed correctly
"""

import asyncio
import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from udp_listener.listener import UDPListener
# Import directly to avoid importing Live module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'remote_script'))
from udp_sender import UDPSender
from osc import (
    build_track_renamed, build_track_mute, build_device_added,
    build_clip_triggered
)


class TestCollector:
    """Collects received events for verification."""

    def __init__(self):
        self.events = []

    async def callback(self, event_path, args, seq_num, timestamp):
        """Store received event."""
        self.events.append({
            "path": event_path,
            "args": args,
            "seq": seq_num,
            "time": timestamp
        })
        print(f"✅ [{seq_num}] {event_path} {args}")


async def test_udp_osc():
    """Run integration test."""
    print("=" * 60)
    print("UDP/OSC Integration Test")
    print("=" * 60)
    print()

    # Create collector
    collector = TestCollector()

    # Start listener
    print("1. Starting UDP listener on port 9002...")
    listener = UDPListener(event_callback=collector.callback)
    listener_task = asyncio.create_task(listener.start())
    await asyncio.sleep(0.5)  # Let listener start
    print("   ✅ Listener started\n")

    # Create sender
    print("2. Creating UDP sender...")
    sender = UDPSender()
    sender.start()
    await asyncio.sleep(0.1)
    print("   ✅ Sender started\n")

    # Send test events
    print("3. Sending test events...")

    # Event 1: Track renamed
    path, *args = build_track_renamed(0, "Bass")
    sender.send_event(path, *args)
    print(f"   Sent: {path} {args}")

    # Event 2: Track mute
    path, *args = build_track_mute(1, True)
    sender.send_event(path, *args)
    print(f"   Sent: {path} {args}")

    # Event 3: Device added
    path, *args = build_device_added(0, 2, "Reverb")
    sender.send_event(path, *args)
    print(f"   Sent: {path} {args}")

    # Event 4: Clip triggered
    path, *args = build_clip_triggered(1, 0)
    sender.send_event(path, *args)
    print(f"   Sent: {path} {args}")

    print()

    # Wait for messages to be received
    await asyncio.sleep(1)

    # Stop sender
    sender.stop()

    # Stop listener
    listener.running = False
    await asyncio.sleep(0.5)

    # Verify results
    print("\n4. Verifying results...")
    print(f"   Events sent: 4")
    print(f"   Events received: {len(collector.events)}\n")

    if len(collector.events) == 4:
        print("✅ All events received!\n")

        # Verify content
        assert collector.events[0]["path"] == "/live/track/renamed"
        assert collector.events[0]["args"] == [0, "Bass"]

        assert collector.events[1]["path"] == "/live/track/mute"
        assert collector.events[1]["args"] == [1, True]

        assert collector.events[2]["path"] == "/live/device/added"
        assert collector.events[2]["args"] == [0, 2, "Reverb"]

        assert collector.events[3]["path"] == "/live/clip/triggered"
        assert collector.events[3]["args"] == [1, 0]

        print("✅ All events parsed correctly!\n")
    else:
        print(f"❌ Expected 4 events, got {len(collector.events)}\n")
        return False

    # Print statistics
    sender_stats = sender.get_stats()
    listener_stats = listener.get_stats()

    print("5. Statistics:")
    print(f"   Sender:")
    print(f"     - Sent: {sender_stats['sent_count']}")
    print(f"     - Errors: {sender_stats['error_count']}")
    print(f"   Listener:")
    print(f"     - Received: {listener_stats['packets_received']}")
    print(f"     - Processed: {listener_stats['packets_processed']}")
    print(f"     - Dropped: {listener_stats['packets_dropped']}")
    print(f"     - Parse errors: {listener_stats['parse_errors']}")
    print(f"   Sequence:")
    print(f"     - Duplicates: {listener_stats['sequence']['duplicates']}")
    print(f"     - Gaps: {listener_stats['sequence']['gaps']}")
    print()

    print("=" * 60)
    print("✅ UDP/OSC Integration Test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_udp_osc())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
