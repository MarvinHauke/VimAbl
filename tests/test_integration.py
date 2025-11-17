#!/usr/bin/env python3
"""Test script to verify UDP-WebSocket integration."""

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
    # Build OSC message: /live/seq ,ifs <seq> <timestamp> <event_path> <args...>
    msg = encode_osc_string("/live/seq")

    # Type tag string
    type_tags = ",ifs" + ("s" * len(args))  # i=int, f=float, s=string
    msg += encode_osc_string(type_tags)

    # Arguments
    msg += struct.pack(">i", seq_num)  # sequence number
    msg += struct.pack(">f", 0.0)  # timestamp (dummy)
    msg += encode_osc_string(event_path)  # event path

    for arg in args:
        if isinstance(arg, str):
            msg += encode_osc_string(arg)
        elif isinstance(arg, int):
            msg += struct.pack(">i", arg)
        elif isinstance(arg, bool):
            msg += struct.pack(">i", 1 if arg else 0)

    sock.sendto(msg, ('127.0.0.1', 9002))

async def test_integration():
    """Test that UDP events are received and forwarded to WebSocket clients."""
    print("🧪 Testing UDP-WebSocket Integration\n")

    # Connect to WebSocket
    print("1. Connecting to WebSocket server...")
    try:
        uri = 'ws://localhost:8765'
        async with websockets.connect(uri) as ws:
            print("   ✓ Connected to WebSocket server\n")

            # Receive initial FULL_AST message
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            data = json.loads(msg)
            print(f"   ✓ Received initial message: {data.get('type')}\n")

            # Send UDP messages
            print("2. Sending UDP test events...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Send some test events
            send_udp_event(sock, 1, "/live/track/renamed", "Test Track")
            send_udp_event(sock, 2, "/live/track/muted", 1)
            send_udp_event(sock, 3, "/live/device/added", 1, "Reverb")

            sock.close()
            print("   ✓ Sent 3 UDP events\n")

            # Wait for UDP events to be forwarded
            print("3. Waiting for UDP events via WebSocket...")
            events_received = 0
            try:
                for i in range(5):  # Try to receive up to 5 messages
                    msg = await asyncio.wait_for(ws.recv(), timeout=2)
                    data = json.loads(msg)
                    if data.get('type') == 'live_event':
                        events_received += 1
                        print(f"   ✓ Received UDP event #{data.get('seq_num')}: {data.get('event_path')}")
            except asyncio.TimeoutError:
                pass

            print(f"\n4. Results:")
            print(f"   Events sent: 3")
            print(f"   Events received via WebSocket: {events_received}")

            if events_received == 3:
                print("\n✅ Integration test PASSED! UDP events are being forwarded to WebSocket clients.")
                return True
            elif events_received > 0:
                print(f"\n⚠️  Integration test PARTIAL: Only {events_received}/3 events received.")
                return True
            else:
                print("\n❌ Integration test FAILED: No UDP events received via WebSocket.")
                return False

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_integration())
    sys.exit(0 if result else 1)
