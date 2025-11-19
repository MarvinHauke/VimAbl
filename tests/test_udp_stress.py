#!/usr/bin/env python3
"""
Stress test for UDP listener - sends rapid bursts of events
to simulate scene reordering (20+ events in quick succession)
"""

import socket
import struct
import time

def pack_osc_string(s):
    """Pack a string in OSC format (null-terminated, 4-byte aligned)."""
    s_bytes = s.encode('utf-8') + b'\x00'
    padding = (4 - len(s_bytes) % 4) % 4
    return s_bytes + (b'\x00' * padding)

def pack_osc_int(i):
    """Pack an integer in OSC format (big-endian 32-bit)."""
    return struct.pack('>i', i)

def pack_osc_float(f):
    """Pack a float in OSC format (big-endian 32-bit)."""
    return struct.pack('>f', f)

def create_sequenced_message(seq_num, timestamp, event_path, *args):
    """Create a sequenced OSC message: /live/seq <seq> <timestamp> <event_path> <args...>"""

    # Start with address pattern
    msg = pack_osc_string("/live/seq")

    # Build type tag string
    type_tags = ",iis"  # int (seq), int (timestamp), string (event_path)
    for arg in args:
        if isinstance(arg, int):
            type_tags += "i"
        elif isinstance(arg, float):
            type_tags += "f"
        elif isinstance(arg, str):
            type_tags += "s"

    msg += pack_osc_string(type_tags)

    # Add arguments
    msg += pack_osc_int(seq_num)
    msg += pack_osc_int(int(timestamp))  # Timestamp in seconds
    msg += pack_osc_string(event_path)

    for arg in args:
        if isinstance(arg, int):
            msg += pack_osc_int(arg)
        elif isinstance(arg, float):
            msg += pack_osc_float(arg)
        elif isinstance(arg, str):
            msg += pack_osc_string(arg)

    return msg

def stress_test():
    """Send rapid bursts of events to simulate scene reordering."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0

    print("🚀 Starting UDP stress test...")
    print("Target: 127.0.0.1:9002")
    print("Simulating scene reorder: 25 rapid events in <10ms\n")

    # Simulate rapid scene reordering (25 events at once)
    start = time.time()
    for i in range(25):
        msg = create_sequenced_message(seq, time.time(), "/live/scene/reordered", i, i+1)
        sock.sendto(msg, ("127.0.0.1", 9002))
        seq += 1
    burst_time = (time.time() - start) * 1000

    print(f"✅ Sent 25 events in {burst_time:.2f}ms (seq 0-24)")

    # Give queue time to process
    time.sleep(0.5)

    # Send another burst
    print("\n🚀 Second burst: 30 events")
    start = time.time()
    for i in range(30):
        msg = create_sequenced_message(seq, time.time(), "/live/clip_slot/highlighted", i % 5, i % 8)
        sock.sendto(msg, ("127.0.0.1", 9002))
        seq += 1
    burst_time = (time.time() - start) * 1000

    print(f"✅ Sent 30 events in {burst_time:.2f}ms (seq 25-54)")

    # Give queue time to process
    time.sleep(0.5)

    print(f"\n📊 Statistics:")
    print(f"  Total sent: {seq}")
    print("\n✅ Stress test complete!")
    print("Check UDP listener logs for gaps/drops")

    sock.close()

if __name__ == "__main__":
    stress_test()
