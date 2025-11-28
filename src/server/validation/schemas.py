"""
Schema definitions for event argument validation.

This module defines the expected structure and types for different
event types coming from Ableton Live.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class EventSchema:
    """
    Schema definition for an event type.

    Attributes:
        required: List of required argument names
        optional: List of optional argument names
        types: Dict mapping argument names to expected types
    """
    required: List[str]
    optional: List[str] = None
    types: Dict[str, type] = None

    def __post_init__(self):
        if self.optional is None:
            self.optional = []
        if self.types is None:
            self.types = {}


# Track-related event schemas
TRACK_ADDED_SCHEMA = EventSchema(
    required=["track_index"],
    optional=["track_name", "track_color"],
    types={"track_index": int, "track_name": str, "track_color": int}
)

TRACK_DELETED_SCHEMA = EventSchema(
    required=["track_index"],
    types={"track_index": int}
)

TRACK_NAME_CHANGED_SCHEMA = EventSchema(
    required=["track_index", "track_name"],
    types={"track_index": int, "track_name": str}
)

TRACK_COLOR_CHANGED_SCHEMA = EventSchema(
    required=["track_index", "track_color"],
    types={"track_index": int, "track_color": int}
)

# Scene-related event schemas
SCENE_ADDED_SCHEMA = EventSchema(
    required=["scene_index"],
    optional=["scene_name"],
    types={"scene_index": int, "scene_name": str}
)

SCENE_REMOVED_SCHEMA = EventSchema(
    required=["scene_index"],
    types={"scene_index": int}
)

SCENE_NAME_CHANGED_SCHEMA = EventSchema(
    required=["scene_index", "scene_name"],
    types={"scene_index": int, "scene_name": str}
)

# Device-related event schemas
DEVICE_ADDED_SCHEMA = EventSchema(
    required=["track_index", "device_index"],
    optional=["device_name", "device_type"],
    types={
        "track_index": int,
        "device_index": int,
        "device_name": str,
        "device_type": str
    }
)

DEVICE_DELETED_SCHEMA = EventSchema(
    required=["track_index", "device_index"],
    types={"track_index": int, "device_index": int}
)

DEVICE_PARAMETER_CHANGED_SCHEMA = EventSchema(
    required=["track_index", "device_index", "parameter_index", "parameter_value"],
    optional=["parameter_name"],
    types={
        "track_index": int,
        "device_index": int,
        "parameter_index": int,
        "parameter_value": float,
        "parameter_name": str
    }
)

# Clip slot related event schemas
CLIP_SLOT_CREATED_SCHEMA = EventSchema(
    required=["track_index", "scene_index"],
    optional=["has_clip", "has_stop_button", "playing_status"],
    types={
        "track_index": int,
        "scene_index": int,
        "has_clip": bool,
        "has_stop_button": bool,
        "playing_status": int
    }
)

CLIP_SLOT_CHANGED_SCHEMA = EventSchema(
    required=["track_index", "scene_index"],
    optional=["has_clip", "has_stop_button", "playing_status"],
    types={
        "track_index": int,
        "scene_index": int,
        "has_clip": bool,
        "has_stop_button": bool,
        "playing_status": int
    }
)

CLIP_NAME_CHANGED_SCHEMA = EventSchema(
    required=["track_index", "scene_index", "clip_name"],
    types={
        "track_index": int,
        "scene_index": int,
        "clip_name": str
    }
)

# Transport-related event schemas
TEMPO_CHANGED_SCHEMA = EventSchema(
    required=["tempo"],
    types={"tempo": float}
)

PLAYBACK_STATE_CHANGED_SCHEMA = EventSchema(
    required=["is_playing"],
    types={"is_playing": bool}
)

# Mixer-related event schemas
VOLUME_CHANGED_SCHEMA = EventSchema(
    required=["track_index", "volume"],
    types={"track_index": int, "volume": float}
)

PAN_CHANGED_SCHEMA = EventSchema(
    required=["track_index", "pan"],
    types={"track_index": int, "pan": float}
)

MUTE_CHANGED_SCHEMA = EventSchema(
    required=["track_index", "is_muted"],
    types={"track_index": int, "is_muted": bool}
)

SOLO_CHANGED_SCHEMA = EventSchema(
    required=["track_index", "is_soloed"],
    types={"track_index": int, "is_soloed": bool}
)

ARM_CHANGED_SCHEMA = EventSchema(
    required=["track_index", "is_armed"],
    types={"track_index": int, "is_armed": bool}
)

# Schema registry mapping event types to schemas
EVENT_SCHEMAS: Dict[str, EventSchema] = {
    # Track events
    "track_added": TRACK_ADDED_SCHEMA,
    "track_deleted": TRACK_DELETED_SCHEMA,
    "track_name_changed": TRACK_NAME_CHANGED_SCHEMA,
    "track_color_changed": TRACK_COLOR_CHANGED_SCHEMA,

    # Scene events
    "scene_added": SCENE_ADDED_SCHEMA,
    "scene_removed": SCENE_REMOVED_SCHEMA,
    "scene_name_changed": SCENE_NAME_CHANGED_SCHEMA,

    # Device events
    "device_added": DEVICE_ADDED_SCHEMA,
    "device_deleted": DEVICE_DELETED_SCHEMA,
    "device_parameter_changed": DEVICE_PARAMETER_CHANGED_SCHEMA,

    # Clip slot events
    "clip_slot_created": CLIP_SLOT_CREATED_SCHEMA,
    "clip_slot_changed": CLIP_SLOT_CHANGED_SCHEMA,
    "clip_name_changed": CLIP_NAME_CHANGED_SCHEMA,

    # Transport events
    "tempo_changed": TEMPO_CHANGED_SCHEMA,
    "playback_state_changed": PLAYBACK_STATE_CHANGED_SCHEMA,

    # Mixer events
    "volume_changed": VOLUME_CHANGED_SCHEMA,
    "pan_changed": PAN_CHANGED_SCHEMA,
    "mute_changed": MUTE_CHANGED_SCHEMA,
    "solo_changed": SOLO_CHANGED_SCHEMA,
    "arm_changed": ARM_CHANGED_SCHEMA,
}
