"""
Constants for the Ableton Live AST server.

This module centralizes magic values and constants used throughout
the event handling and AST manipulation code.
"""

from enum import IntEnum


class EventConstants:
    """Constants for event handling and processing."""

    # Debouncing
    DEBOUNCE_DELAY_SECONDS = 0.1  # 100ms debounce for parameter updates

    # Default values
    DEFAULT_DEVICE_TYPE = "unknown"
    DEFAULT_TEMPO = 120.0
    DEFAULT_COLOR = -1
    DEFAULT_TIME_SIGNATURE_ID = 201

    # Clip defaults
    DEFAULT_CLIP_NAME = "Untitled"
    DEFAULT_CLIP_TYPE = "midi"
    DEFAULT_CLIP_VIEW = "session"
    DEFAULT_WARP_MODE = "Unknown"

    # Mixer defaults
    DEFAULT_VOLUME = 1.0
    DEFAULT_PAN = 0.0
    DEFAULT_CROSSFADER = "None"


class PlayingStatus(IntEnum):
    """Clip slot playing status codes from Ableton Live."""
    STOPPED = 0
    PLAYING = 1
    TRIGGERED = 2


class NodeIDPatterns:
    """
    Patterns and helpers for generating consistent node IDs.

    Node IDs should be stable and predictable where possible to enable
    reliable diff tracking and node identification.
    """

    @staticmethod
    def track(index: int) -> str:
        """Generate a track node ID."""
        return f"track_{index}"

    @staticmethod
    def device(track_idx: int, device_idx: int, seq_num: int = None) -> str:
        """
        Generate a device node ID.

        Args:
            track_idx: Track index
            device_idx: Device index within track
            seq_num: Optional sequence number for uniqueness
        """
        if seq_num is not None:
            return f"device_{track_idx}_{device_idx}_{seq_num}"
        return f"device_{track_idx}_{device_idx}"

    @staticmethod
    def scene(uuid_hex: str) -> str:
        """Generate a scene node ID with UUID."""
        return f"scene_{uuid_hex}"

    @staticmethod
    def clip_slot(uuid_hex: str) -> str:
        """Generate a clip slot node ID with UUID."""
        return f"clip_slot_{uuid_hex}"

    @staticmethod
    def clip(track_idx: int, scene_idx: int) -> str:
        """Generate a clip node ID."""
        return f"clip_{track_idx}_{scene_idx}"

    @staticmethod
    def mixer(track_idx: int) -> str:
        """Generate a mixer node ID."""
        return f"mixer_{track_idx}"

    @staticmethod
    def file_ref(hash_hex: str = None, index: int = None) -> str:
        """
        Generate a file reference node ID.

        Args:
            hash_hex: First 8 chars of file hash (preferred)
            index: Fallback numeric index
        """
        if hash_hex:
            return f"fileref_{hash_hex[:8]}"
        return f"fileref_{index}"


class TrackType:
    """Track type constants."""
    REGULAR = "regular"
    RETURN = "return"
    MASTER = "master"


class ClipType:
    """Clip type constants."""
    MIDI = "midi"
    AUDIO = "audio"
