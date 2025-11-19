"""
UDP listener service for receiving OSC events from Ableton Live.

Listens on UDP port 9002 for OSC messages, parses them, deduplicates based on
sequence numbers, and forwards events to the AST server for processing.
"""

import asyncio
import socket
import logging
from typing import Optional, Callable, Dict, Any
from collections import deque

try:
    from .osc_parser import parse_osc_message, parse_sequenced_message, OSCMessage
except ImportError:
    # For testing outside of package context
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from osc_parser import parse_osc_message, parse_sequenced_message, OSCMessage


logger = logging.getLogger(__name__)


class SequenceTracker:
    """
    Tracks sequence numbers to detect duplicates and gaps.
    """

    def __init__(self, buffer_size: int = 100):
        """
        Initialize sequence tracker.

        Args:
            buffer_size: Number of recent sequence numbers to remember
        """
        self.buffer_size = buffer_size
        self.seen = deque(maxlen=buffer_size)
        self.last_seq = -1
        self.stats = {
            "total_received": 0,
            "duplicates": 0,
            "gaps": 0,
            "gap_size_total": 0
        }

    def process(self, seq_num: int) -> Dict[str, Any]:
        """
        Process a sequence number and detect duplicates/gaps.

        Args:
            seq_num: Sequence number to process

        Returns:
            dict: Status with keys: is_duplicate, gap_size, stats
        """
        self.stats["total_received"] += 1

        # Check for duplicate
        if seq_num in self.seen:
            self.stats["duplicates"] += 1
            return {
                "is_duplicate": True,
                "gap_size": 0,
                "stats": self.stats.copy()
            }

        # Add to seen buffer
        self.seen.append(seq_num)

        # Detect gap
        gap_size = 0
        if self.last_seq != -1:
            expected = self.last_seq + 1
            gap_size = seq_num - expected

            if gap_size > 0:
                self.stats["gaps"] += 1
                self.stats["gap_size_total"] += gap_size
                logger.warning(f"Gap detected: expected seq {expected}, got {seq_num} (gap: {gap_size})")
            elif gap_size < -1:
                # Out of order, but within tolerance
                logger.debug(f"Out of order sequence: expected seq {expected}, got {seq_num}")

        self.last_seq = max(self.last_seq, seq_num)

        return {
            "is_duplicate": False,
            "gap_size": gap_size,
            "stats": self.stats.copy()
        }


class UDPListener:
    """
    Async UDP listener for OSC messages.

    Receives UDP packets, parses OSC messages, deduplicates based on sequence
    numbers, and forwards events to a callback for processing.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9002,
        event_callback: Optional[Callable] = None
    ):
        """
        Initialize UDP listener.

        Args:
            host: Host to bind to (default: 0.0.0.0 for all interfaces)
            port: UDP port to listen on (default: 9002)
            event_callback: Async callback for processed events:
                            callback(event_path, args, seq_num, timestamp)
        """
        self.host = host
        self.port = port
        self.event_callback = event_callback
        self.running = False
        self.socket: Optional[socket.socket] = None
        self.sequence_tracker = SequenceTracker()

        # Event queue for non-blocking processing
        # This prevents slow WebSocket broadcasts from blocking UDP receives
        self._event_queue: asyncio.Queue = None
        self._processor_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats = {
            "packets_received": 0,
            "packets_processed": 0,
            "packets_dropped": 0,
            "parse_errors": 0,
            "queue_size": 0,
            "queue_max": 0
        }

    async def start(self):
        """Start the UDP listener."""
        self.running = True

        # Create event queue for non-blocking processing
        # This prevents slow WebSocket broadcasts from blocking UDP receives
        self._event_queue = asyncio.Queue(maxsize=1000)

        # Create UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.setblocking(False)

        logger.info(f"UDP listener started on {self.host}:{self.port}")

        # Start event processor task
        self._processor_task = asyncio.create_task(self._event_processor())

        # Start receive loop
        await self._receive_loop()

    async def stop(self):
        """Stop the UDP listener."""
        self.running = False

        # Cancel event processor task
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None

        # Log queue stats before shutting down
        if self._event_queue:
            queue_size = self._event_queue.qsize()
            if queue_size > 0:
                logger.warning(f"Shutting down with {queue_size} events still in queue")

        if self.socket:
            self.socket.close()
            self.socket = None
        logger.info("UDP listener stopped")

    async def _receive_loop(self):
        """Main receive loop."""
        loop = asyncio.get_event_loop()

        while self.running:
            try:
                # Receive UDP packet (non-blocking with timeout)
                data, addr = await loop.sock_recvfrom(self.socket, 4096)
                self.stats["packets_received"] += 1

                # Process packet (parse and queue for processing)
                await self._process_packet(data, addr)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                await asyncio.sleep(0.1)

    async def _event_processor(self):
        """
        Process events from the queue in a separate task.

        This runs concurrently with UDP reception, preventing slow WebSocket
        broadcasts from blocking UDP packet receives.
        """
        logger.info("Event processor started")

        while self.running:
            try:
                # Get event from queue (with timeout to check running flag)
                try:
                    event_data = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue

                # Unpack event data
                event_path, event_args, seq_num, timestamp = event_data

                # Call the event callback (may be slow due to WebSocket broadcast)
                if self.event_callback:
                    await self.event_callback(event_path, event_args, seq_num, timestamp)

                # Update queue stats
                self.stats["queue_size"] = self._event_queue.qsize()

            except asyncio.CancelledError:
                logger.info("Event processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in event processor: {e}")
                await asyncio.sleep(0.1)

        logger.info("Event processor stopped")

    async def _process_packet(self, data: bytes, addr: tuple):
        """
        Process a received UDP packet.

        Args:
            data: Raw packet data
            addr: Source address tuple
        """
        try:
            # Parse OSC message
            msg = parse_osc_message(data)

            # Handle batch markers
            if msg.address == "/live/batch/start":
                logger.debug(f"Batch start: {msg.arguments[0]}")
                self.stats["packets_processed"] += 1
                return
            elif msg.address == "/live/batch/end":
                logger.debug(f"Batch end: {msg.arguments[0]}")
                self.stats["packets_processed"] += 1
                return

            # Parse sequenced message
            if msg.address == "/live/seq":
                seq_num, timestamp, event_path, event_args = parse_sequenced_message(data)

                # Check for duplicates/gaps
                seq_status = self.sequence_tracker.process(seq_num)

                if seq_status["is_duplicate"]:
                    logger.debug(f"Dropping duplicate seq {seq_num}")
                    self.stats["packets_dropped"] += 1
                    return

                if seq_status["gap_size"] > 0:
                    logger.warning(f"Gap of {seq_status['gap_size']} messages detected at seq {seq_num}")

                # Queue event for processing (non-blocking)
                # This prevents slow WebSocket broadcasts from blocking UDP receives
                try:
                    self._event_queue.put_nowait((event_path, event_args, seq_num, timestamp))
                    self.stats["queue_size"] = self._event_queue.qsize()
                    self.stats["queue_max"] = max(self.stats["queue_max"], self.stats["queue_size"])
                except asyncio.QueueFull:
                    logger.error(f"Event queue full! Dropping event {event_path} seq={seq_num}")
                    self.stats["packets_dropped"] += 1
                    return

                self.stats["packets_processed"] += 1

            else:
                # Non-sequenced message (shouldn't happen normally)
                logger.warning(f"Received non-sequenced message: {msg.address}")
                self.stats["packets_processed"] += 1

        except Exception as e:
            logger.error(f"Failed to process packet: {e}")
            self.stats["parse_errors"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """
        Get listener statistics.

        Returns:
            dict: Statistics including packets, sequences, gaps, etc.
        """
        return {
            **self.stats,
            "sequence": self.sequence_tracker.stats
        }


async def example_event_callback(event_path: str, args: list, seq_num: int, timestamp: float):
    """Example callback for testing."""
    print(f"[{seq_num}] {event_path} {args}")


async def main():
    """Test the UDP listener."""
    print("Starting UDP listener test...")
    print("Send test messages with: python3 src/remote_script/udp_sender.py")
    print("Press Ctrl+C to stop\n")

    listener = UDPListener(event_callback=example_event_callback)

    try:
        await listener.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await listener.stop()

        # Print stats
        stats = listener.get_stats()
        print("\nStatistics:")
        print(f"  Packets received: {stats['packets_received']}")
        print(f"  Packets processed: {stats['packets_processed']}")
        print(f"  Packets dropped: {stats['packets_dropped']}")
        print(f"  Parse errors: {stats['parse_errors']}")
        print(f"  Sequence duplicates: {stats['sequence']['duplicates']}")
        print(f"  Sequence gaps: {stats['sequence']['gaps']}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )
    asyncio.run(main())
