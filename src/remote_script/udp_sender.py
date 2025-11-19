"""
UDP sender for emitting OSC events from Ableton Live Remote Script.

This module provides a non-blocking UDP socket for sending real-time events
to the UDP listener service without blocking Ableton's main thread.

PERFORMANCE TUNING:
-------------------
Logging is controlled centrally in logging_config.py
Set ENABLE_LOGGING = False for better performance
"""

import socket
import time
from typing import Any, Optional

try:
    from .osc import build_sequenced_message
    from .logging_config import log
except ImportError:
    # For testing outside of package context
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from osc import build_sequenced_message
    # Fallback logging function for standalone testing
    def log(component: str, message: str, level: str = "INFO", force: bool = False):
        print(f"[{level}] [{component}] {message}")


class UDPSender:
    """
    Non-blocking UDP sender for OSC events.

    Sends fire-and-forget UDP packets to the UDP listener service.
    Never blocks - if send fails, logs error and continues.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9002):
        """
        Initialize UDP sender.

        Args:
            host: Target host (default: localhost)
            port: Target UDP port (default: 9002)
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.seq_num = 0
        self.enabled = False

        # Statistics
        self.sent_count = 0
        self.error_count = 0

    def start(self):
        """Initialize UDP socket and enable sending."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Set non-blocking mode
            self.socket.setblocking(False)
            self.enabled = True
            self.log("UDP sender started on {}:{}".format(self.host, self.port))
        except Exception as e:
            self.log("Failed to start UDP sender: {}".format(str(e)))
            self.enabled = False

    def stop(self):
        """Close UDP socket and disable sending."""
        self.enabled = False
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                self.log("Error closing UDP socket: {}".format(str(e)))
            finally:
                self.socket = None
        self.log("UDP sender stopped")

    def send_event(self, event_path: str, *args: Any) -> bool:
        """
        Send an OSC event via UDP (fire-and-forget).

        Args:
            event_path: OSC address pattern (e.g., "/live/track/renamed")
            *args: Event arguments (int, float, str, bool)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.enabled or not self.socket:
            return False

        try:
            # Build OSC message with sequence number
            message = build_sequenced_message(self.seq_num, event_path, *args)

            # Send via UDP (non-blocking, fire-and-forget)
            self.socket.sendto(message, (self.host, self.port))

            # Update sequence number and stats
            self.seq_num += 1
            self.sent_count += 1

            # Log scene events for debugging
            if "/scene/" in event_path:
                log("UDPSender", f"Sent: {event_path} {args}", level="INFO", force=True)

            return True

        except Exception as e:
            self.error_count += 1
            self.log("Failed to send UDP message: {}".format(str(e)))
            return False

    def send_batch(self, batch_id: int, events: list):
        """
        Send a batch of events grouped together.

        Args:
            batch_id: Unique batch identifier
            events: List of (event_path, *args) tuples
        """
        if not self.enabled:
            return

        # Import here to avoid circular dependency
        try:
            from .osc import build_batch_start, build_batch_end
        except ImportError:
            from osc import build_batch_start, build_batch_end

        try:
            # Send batch start marker
            if self.socket:
                batch_start = build_batch_start(batch_id)
                self.socket.sendto(batch_start, (self.host, self.port))

            # Send all events
            for event_data in events:
                if len(event_data) >= 1:
                    event_path = event_data[0]
                    args = event_data[1:] if len(event_data) > 1 else ()
                    self.send_event(event_path, *args)

            # Send batch end marker
            if self.socket:
                batch_end = build_batch_end(batch_id)
                self.socket.sendto(batch_end, (self.host, self.port))

        except Exception as e:
            self.log("Failed to send batch: {}".format(str(e)))

    def get_stats(self) -> dict:
        """
        Get sender statistics.

        Returns:
            dict: Statistics including sent_count, error_count, seq_num
        """
        return {
            "enabled": self.enabled,
            "sent_count": self.sent_count,
            "error_count": self.error_count,
            "seq_num": self.seq_num,
            "host": self.host,
            "port": self.port
        }

    def log(self, message: str, force: bool = False):
        """
        Log message using centralized logging config.

        Args:
            message: Message to log
            force: If True, log even if logging is disabled (for critical errors)
        """
        level = "ERROR" if force else "INFO"
        log("UDPSender", message, level=level, force=force)


# Singleton instance (initialized by LiveState.py)
_sender_instance: Optional[UDPSender] = None


def get_sender() -> Optional[UDPSender]:
    """Get the global UDP sender instance."""
    return _sender_instance


def init_sender(host: str = "127.0.0.1", port: int = 9002) -> UDPSender:
    """
    Initialize the global UDP sender instance.

    Args:
        host: Target host
        port: Target UDP port

    Returns:
        UDPSender: The initialized sender instance
    """
    global _sender_instance
    if _sender_instance is None:
        _sender_instance = UDPSender(host, port)
        _sender_instance.start()
    return _sender_instance


def shutdown_sender():
    """Shutdown the global UDP sender instance."""
    global _sender_instance
    if _sender_instance:
        _sender_instance.stop()
        _sender_instance = None


if __name__ == "__main__":
    # Test the UDP sender
    print("Testing UDP sender...")
    print("NOTE: Start a UDP listener to see messages: nc -u -l 9002")
    print()

    # Create sender
    sender = UDPSender()
    sender.start()

    # Send test events
    print("Sending test events...")
    sender.send_event("/live/track/renamed", 0, "Bass")
    sender.send_event("/live/track/mute", 0, True)
    sender.send_event("/live/device/added", 0, 1, "Reverb")

    # Send batch
    print("Sending batch...")
    batch_events = [
        ("/live/track/added", 0, "Audio 1", "audio"),
        ("/live/track/added", 1, "Audio 2", "audio"),
        ("/live/track/added", 2, "MIDI 1", "midi"),
    ]
    sender.send_batch(1001, batch_events)

    # Print stats
    stats = sender.get_stats()
    print("\nStatistics:")
    print("  Sent: {}".format(stats["sent_count"]))
    print("  Errors: {}".format(stats["error_count"]))
    print("  Sequence: {}".format(stats["seq_num"]))

    # Cleanup
    sender.stop()
    print("\n✅ UDP sender test complete!")
