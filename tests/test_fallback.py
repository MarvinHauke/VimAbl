#!/usr/bin/env python3
"""Test script to verify fallback mechanism when UDP events are missed."""

import asyncio
import websockets
import json
import sys
import socket
import struct

def encode_osc_string(s):
    """Encode a string in OSC format (null-terminated, padded to 4 bytes)."""
    s_bytes = s.encode('utf-8') + b'\x00'
    padding = (4 - len(s_bytes) % 4) % 4
    return s_bytes + (b'\x00' * padding)

def send_udp_event(sock, seq_num, event_path, *args):
    """Send a sequenced OSC message via UDP."""
    msg = encode_osc_string("/live/seq")
    type_tags = ",ifs" + ("s" * len(args))
    msg += encode_osc_string(type_tags)
    msg += struct.pack(">i", seq_num)
    msg += struct.pack(">f", 0.0)
    msg += encode_osc_string(event_path)

    for arg in args:
        if isinstance(arg, str):
            msg += encode_osc_string(arg)
        elif isinstance(arg, int):
            msg += struct.pack(">i", arg)
        elif isinstance(arg, bool):
            msg += struct.pack(">i", 1 if arg else 0)

    sock.sendto(msg, ('127.0.0.1', 9002))

async def test_fallback():
    """Test that gaps trigger fallback warning."""
    print("🧪 Testing UDP Fallback Mechanism\n")

    try:
        uri = 'ws://localhost:8765'
        async with websockets.connect(uri) as ws:
            print("✓ Connected to WebSocket server\n")

            # Receive initial message
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            data = json.loads(msg)
            print(f"✓ Received initial message: {data.get('type')}\n")

            # Send events with a large gap
            print("Sending events with gaps...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            send_udp_event(sock, 1, "/live/track/renamed", "Track 1")
            print("  Sent event #1")

            send_udp_event(sock, 2, "/live/track/renamed", "Track 2")
            print("  Sent event #2")

            # Skip events 3-9 (gap of 7)
            send_udp_event(sock, 10, "/live/track/renamed", "Track 10")
            print("  Sent event #10 (gap of 7 from #2)")

            sock.close()
            print("\n✓ Sent events with gap\n")

            # Wait for events and error message
            print("Waiting for events and fallback warning...")
            received_error = False
            events_count = 0

            try:
                for i in range(10):
                    msg = await asyncio.wait_for(ws.recv(), timeout=2)
                    data = json.loads(msg)

                    if data.get('type') == 'live_event':
                        events_count += 1
                        seq = data.get('seq_num')
                        print(f"  ✓ Received event #{seq}")
                    elif data.get('type') == 'error':
                        received_error = True
                        error = data.get('error', '')
                        details = data.get('details', '')
                        print(f"  ✓ Received fallback warning: {error}")
                        print(f"    Details: {details}")
            except asyncio.TimeoutError:
                pass

            print(f"\nResults:")
            print(f"  Events received: {events_count}")
            print(f"  Fallback warning received: {received_error}")

            if received_error:
                print("\n✅ Fallback test PASSED! Gap detection triggered warning.")
                return True
            else:
                print("\n❌ Fallback test FAILED: No warning received for gap.")
                return False

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_fallback())
    sys.exit(0 if result else 1)
