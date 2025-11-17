"""
OSC (Open Sound Control) message parser.

Parses binary OSC messages received via UDP into structured Python data.

Reference: http://opensoundcontrol.org/spec-1_0
"""

import struct
from typing import Any, List, Tuple, Union
from dataclasses import dataclass


@dataclass
class OSCMessage:
    """Parsed OSC message."""
    address: str
    type_tags: str
    arguments: List[Any]


def _read_string(data: bytes, offset: int) -> Tuple[str, int]:
    """
    Read OSC string from bytes (null-terminated, padded to 4 bytes).

    Returns:
        Tuple of (string, new_offset)
    """
    # Find null terminator
    null_idx = data.find(b'\x00', offset)
    if null_idx == -1:
        raise ValueError("No null terminator found for OSC string")

    # Extract string
    string = data[offset:null_idx].decode('utf-8')

    # Calculate next offset (padded to multiple of 4)
    string_len = null_idx - offset + 1  # Include null terminator
    padding = (4 - (string_len % 4)) % 4
    new_offset = null_idx + 1 + padding

    return string, new_offset


def _read_int(data: bytes, offset: int) -> Tuple[int, int]:
    """
    Read OSC int32 (big-endian).

    Returns:
        Tuple of (int, new_offset)
    """
    value = struct.unpack('>i', data[offset:offset+4])[0]
    return value, offset + 4


def _read_float(data: bytes, offset: int) -> Tuple[float, int]:
    """
    Read OSC float32 (big-endian).

    Returns:
        Tuple of (float, new_offset)
    """
    value = struct.unpack('>f', data[offset:offset+4])[0]
    return value, offset + 4


def parse_osc_message(data: bytes) -> OSCMessage:
    """
    Parse binary OSC message into structured data.

    Args:
        data: Raw bytes from UDP packet

    Returns:
        OSCMessage: Parsed message with address, type tags, and arguments

    Raises:
        ValueError: If message format is invalid

    Example:
        >>> data = b'/live/track/renamed\\x00,is\\x00\\x00\\x00\\x00\\x00\\x00Bass\\x00\\x00\\x00\\x00'
        >>> msg = parse_osc_message(data)
        >>> print(msg.address, msg.arguments)
        /live/track/renamed [0, 'Bass']
    """
    if len(data) < 8:
        raise ValueError(f"OSC message too short: {len(data)} bytes")

    offset = 0

    # Read address pattern
    address, offset = _read_string(data, offset)
    if not address.startswith('/'):
        raise ValueError(f"OSC address must start with '/': {address}")

    # Read type tag string
    type_tags, offset = _read_string(data, offset)
    if not type_tags.startswith(','):
        raise ValueError(f"OSC type tags must start with ',': {type_tags}")

    # Remove leading comma
    type_tags = type_tags[1:]

    # Parse arguments based on type tags
    arguments = []
    for tag in type_tags:
        if tag == 'i':
            value, offset = _read_int(data, offset)
            arguments.append(value)
        elif tag == 'f':
            value, offset = _read_float(data, offset)
            arguments.append(value)
        elif tag == 's':
            value, offset = _read_string(data, offset)
            arguments.append(value)
        elif tag == 'T':
            arguments.append(True)
            # No data for booleans
        elif tag == 'F':
            arguments.append(False)
            # No data for booleans
        else:
            raise ValueError(f"Unsupported OSC type tag: {tag}")

    return OSCMessage(address=address, type_tags=type_tags, arguments=arguments)


def parse_sequenced_message(data: bytes) -> Tuple[int, float, str, List[Any]]:
    """
    Parse sequenced OSC message (format: /live/seq <seq> <time> <path> <args...>).

    Args:
        data: Raw bytes from UDP packet

    Returns:
        Tuple of (seq_num, timestamp, event_path, event_args)

    Raises:
        ValueError: If not a valid sequenced message
    """
    msg = parse_osc_message(data)

    if msg.address != "/live/seq":
        raise ValueError(f"Not a sequenced message: {msg.address}")

    if len(msg.arguments) < 3:
        raise ValueError(f"Sequenced message needs at least 3 args, got {len(msg.arguments)}")

    seq_num = msg.arguments[0]
    timestamp = msg.arguments[1]
    event_path = msg.arguments[2]
    event_args = msg.arguments[3:] if len(msg.arguments) > 3 else []

    if not isinstance(seq_num, int):
        raise ValueError(f"Sequence number must be int, got {type(seq_num)}")
    if not isinstance(timestamp, (int, float)):
        raise ValueError(f"Timestamp must be numeric, got {type(timestamp)}")
    if not isinstance(event_path, str):
        raise ValueError(f"Event path must be string, got {type(event_path)}")

    return seq_num, timestamp, event_path, event_args


if __name__ == "__main__":
    # Test the OSC parser
    print("Testing OSC parser...")

    # Test data from our UDP sender
    test_messages = [
        # Track renamed: /live/track/renamed 0 "Bass"
        bytes.fromhex("2f6c6976652f747261636b2f72656e616d6564002c697300000000004261737300000000"),
        # Track mute: /live/track/mute 0 True
        bytes.fromhex("2f6c6976652f747261636b2f6d757465000000002c69540000000000"),
        # Sequenced message
        bytes.fromhex("2f6c6976652f7365710000002c696673697300000000002a4ed228d32f6c6976652f747261636b2f72656e616d656400000000004261737300000000"),
    ]

    # Test basic parsing
    msg1 = parse_osc_message(test_messages[0])
    print(f"\n✅ Message 1: {msg1.address}")
    print(f"   Args: {msg1.arguments}")
    assert msg1.address == "/live/track/renamed"
    assert msg1.arguments == [0, "Bass"]

    msg2 = parse_osc_message(test_messages[1])
    print(f"\n✅ Message 2: {msg2.address}")
    print(f"   Args: {msg2.arguments}")
    assert msg2.address == "/live/track/mute"
    assert msg2.arguments == [0, True]

    # Test sequenced parsing
    seq_num, timestamp, event_path, event_args = parse_sequenced_message(test_messages[2])
    print(f"\n✅ Sequenced message:")
    print(f"   Seq: {seq_num}, Time: {timestamp}")
    print(f"   Event: {event_path}")
    print(f"   Args: {event_args}")
    assert seq_num == 42
    assert event_path == "/live/track/renamed"
    assert event_args == [0, "Bass"]

    print("\n✅ All OSC parser tests passed!")
