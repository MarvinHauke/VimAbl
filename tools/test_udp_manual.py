#!/usr/bin/env python3
"""
Manual UDP sender test - sends test events to verify UDP listener is working
"""

import sys
import os

# Add remote_script to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'remote_script'))

from udp_sender import UDPSender
import time

def main():
    print("=" * 60)
    print("Manual UDP Test - Sending Test Events")
    print("=" * 60)
    print()
    print("This script sends test UDP events to verify your listener works.")
    print("Make sure your UDP listener is running:")
    print("  python3 src/udp_listener/listener.py")
    print()

    # Create sender
    sender = UDPSender(host="127.0.0.1", port=9002)
    sender.start()
    print("✓ UDP sender started")
    print()

    # Send test events
    events = [
        ("/live/track/renamed", [0, "Test Track"]),
        ("/live/track/mute", [0, True]),
        ("/live/track/arm", [1, True]),
        ("/live/track/volume", [0, 0.75]),
        ("/live/device/added", [0, 0, "Reverb"]),
        ("/live/device/param", [0, 0, 2, 0.5]),
        ("/live/transport/play", [True]),
        ("/live/transport/tempo", [128.0]),
    ]

    print("Sending 8 test events...")
    for path, args in events:
        sender.send_event(path, *args)
        print(f"  → Sent: {path} {args}")
        time.sleep(0.1)

    print()
    print("✓ All events sent!")
    print()

    # Show stats
    stats = sender.get_stats()
    print("Statistics:")
    print(f"  Sent: {stats['sent']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Last seq: {stats['seq_num']}")
    print()

    sender.stop()
    print("✓ UDP sender stopped")
    print()
    print("Check your UDP listener - you should see 8 events.")
    print("=" * 60)

if __name__ == "__main__":
    main()
