"""
OSC (Open Sound Control) message builder for UDP communication.

This module provides utilities for encoding messages in the OSC protocol format.
OSC messages consist of an address pattern, type tags, and arguments.

Reference: http://opensoundcontrol.org/spec-1_0
"""

import struct
import time
from typing import Any, List, Union


def _pad_to_multiple_of_4(data: bytes) -> bytes:
    """Pad bytes to a multiple of 4 bytes with null bytes."""
    remainder = len(data) % 4
    if remainder != 0:
        data += b'\x00' * (4 - remainder)
    return data


def _encode_string(s: str) -> bytes:
    """Encode a string as OSC string (null-terminated, padded to 4 bytes)."""
    # Convert to bytes and add null terminator
    encoded = s.encode('utf-8') + b'\x00'
    # Pad to multiple of 4
    return _pad_to_multiple_of_4(encoded)


def _encode_int(i: int) -> bytes:
    """Encode an integer as OSC int32 (big-endian)."""
    return struct.pack('>i', i)


def _encode_float(f: float) -> bytes:
    """Encode a float as OSC float32 (big-endian)."""
    return struct.pack('>f', f)


def _encode_bool(b: bool) -> bytes:
    """Encode a boolean as OSC bool (no data, just type tag T or F)."""
    # Booleans have no data in OSC, only the type tag matters
    return b''


def build_osc_message(address: str, *args: Any) -> bytes:
    """
    Build an OSC message with the given address pattern and arguments.

    Args:
        address: OSC address pattern (e.g., "/live/track/renamed")
        *args: Variable arguments (int, float, str, bool)

    Returns:
        bytes: Complete OSC message ready to send via UDP

    Example:
        >>> msg = build_osc_message("/live/track/renamed", 0, "Bass")
        >>> # Returns bytes representing: /live/track/renamed,is\x00\x00\x00\x00\x00\x00Bass\x00\x00\x00\x00
    """
    if not address.startswith('/'):
        raise ValueError(f"OSC address must start with '/': {address}")

    # Encode address pattern
    message = _encode_string(address)

    # Build type tag string
    type_tags = ','
    encoded_args = []

    for arg in args:
        if isinstance(arg, bool):
            # Booleans use T/F tags and have no data
            type_tags += 'T' if arg else 'F'
            encoded_args.append(_encode_bool(arg))
        elif isinstance(arg, int):
            type_tags += 'i'
            encoded_args.append(_encode_int(arg))
        elif isinstance(arg, float):
            type_tags += 'f'
            encoded_args.append(_encode_float(arg))
        elif isinstance(arg, str):
            type_tags += 's'
            encoded_args.append(_encode_string(arg))
        else:
            raise TypeError(f"Unsupported OSC argument type: {type(arg)}")

    # Encode type tag string
    message += _encode_string(type_tags)

    # Append encoded arguments
    for encoded_arg in encoded_args:
        message += encoded_arg

    return message


def build_sequenced_message(seq_num: int, event_path: str, *args: Any) -> bytes:
    """
    Build an OSC message with sequence number wrapper.

    Format: /live/seq <seq_num:int> <timestamp:float> <event_path:str> <args...>

    Args:
        seq_num: Sequence number (monotonically increasing)
        event_path: Event address pattern (e.g., "/live/track/renamed")
        *args: Event arguments

    Returns:
        bytes: Complete OSC message with sequence wrapper

    Example:
        >>> msg = build_sequenced_message(42, "/live/track/renamed", 0, "Bass")
        >>> # Returns: /live/seq,ifs...\x00\x00\x00*...
    """
    timestamp = time.time()

    # Combine sequence metadata with event path and args
    all_args = [seq_num, timestamp, event_path] + list(args)

    return build_osc_message("/live/seq", *all_args)


def build_batch_start(batch_id: int) -> bytes:
    """Build OSC message for batch start."""
    return build_osc_message("/live/batch/start", batch_id)


def build_batch_end(batch_id: int) -> bytes:
    """Build OSC message for batch end."""
    return build_osc_message("/live/batch/end", batch_id)


# Event builder helper functions
def build_track_renamed(track_idx: int, name: str) -> str:
    """Build event path and args for track renamed event."""
    return ("/live/track/renamed", track_idx, name)


def build_track_added(track_idx: int, name: str, track_type: str) -> tuple:
    """Build event path and args for track added event."""
    return ("/live/track/added", track_idx, name, track_type)


def build_track_deleted(track_idx: int) -> tuple:
    """Build event path and args for track deleted event."""
    return ("/live/track/deleted", track_idx)


def build_track_mute(track_idx: int, muted: bool) -> tuple:
    """Build event path and args for track mute event."""
    return ("/live/track/mute", track_idx, muted)


def build_track_arm(track_idx: int, armed: bool) -> tuple:
    """Build event path and args for track arm event."""
    return ("/live/track/arm", track_idx, armed)


def build_track_volume(track_idx: int, volume: float) -> tuple:
    """Build event path and args for track volume event."""
    return ("/live/track/volume", track_idx, volume)


def build_device_added(track_idx: int, device_idx: int, name: str) -> tuple:
    """Build event path and args for device added event."""
    return ("/live/device/added", track_idx, device_idx, name)


def build_device_deleted(track_idx: int, device_idx: int) -> tuple:
    """Build event path and args for device deleted event."""
    return ("/live/device/deleted", track_idx, device_idx)


def build_device_param(track_idx: int, device_idx: int, param_id: int, value: float) -> tuple:
    """Build event path and args for device parameter change event."""
    return ("/live/device/param", track_idx, device_idx, param_id, value)


def build_clip_triggered(track_idx: int, scene_idx: int) -> tuple:
    """Build event path and args for clip triggered event."""
    return ("/live/clip/triggered", track_idx, scene_idx)


def build_clip_stopped(track_idx: int, scene_idx: int) -> tuple:
    """Build event path and args for clip stopped event."""
    return ("/live/clip/stopped", track_idx, scene_idx)


def build_clip_added(track_idx: int, scene_idx: int, name: str) -> tuple:
    """Build event path and args for clip added event."""
    return ("/live/clip/added", track_idx, scene_idx, name)


def build_clip_deleted(track_idx: int, scene_idx: int) -> tuple:
    """Build event path and args for clip deleted event."""
    return ("/live/clip/deleted", track_idx, scene_idx)


def build_scene_renamed(scene_idx: int, name: str) -> tuple:
    """Build event path and args for scene renamed event."""
    return ("/live/scene/renamed", scene_idx, name)


def build_scene_triggered(scene_idx: int) -> tuple:
    """Build event path and args for scene triggered event."""
    return ("/live/scene/triggered", scene_idx)


def build_transport_play(is_playing: bool) -> tuple:
    """Build event path and args for transport play/stop event."""
    return ("/live/transport/play", is_playing)


def build_transport_tempo(bpm: float) -> tuple:
    """Build event path and args for transport tempo event."""
    return ("/live/transport/tempo", bpm)


def build_transport_position(beats: float) -> tuple:
    """Build event path and args for transport position event."""
    return ("/live/transport/position", beats)


if __name__ == "__main__":
    # Test the OSC message builder
    print("Testing OSC message builder...")

    # Test basic message
    msg = build_osc_message("/live/track/renamed", 0, "Bass")
    print(f"Track renamed message: {len(msg)} bytes")
    print(f"  Hex: {msg.hex()}")

    # Test sequenced message
    seq_msg = build_sequenced_message(42, "/live/track/renamed", 0, "Bass")
    print(f"\nSequenced message: {len(seq_msg)} bytes")
    print(f"  Hex: {seq_msg.hex()}")

    # Test boolean message
    mute_msg = build_osc_message("/live/track/mute", 0, True)
    print(f"\nMute message: {len(mute_msg)} bytes")
    print(f"  Hex: {mute_msg.hex()}")

    # Test batch messages
    batch_start = build_batch_start(1001)
    batch_end = build_batch_end(1001)
    print(f"\nBatch start: {len(batch_start)} bytes")
    print(f"Batch end: {len(batch_end)} bytes")

    print("\n✅ OSC message builder tests passed!")
