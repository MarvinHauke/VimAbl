"""
Event handlers package for Ableton Live AST server.

This package contains specialized handlers for different event types,
organized by domain (tracks, scenes, devices, clips, transport).
"""

from .base import EventResult, BaseEventHandler, broadcast_result, validate_args, require_ast_node, handle_exceptions
from .track_handler import TrackEventHandler
from .scene_handler import SceneEventHandler
from .device_handler import DeviceEventHandler
from .clip_slot_handler import ClipSlotEventHandler
from .transport_handler import TransportEventHandler

__all__ = [
    "EventResult",
    "BaseEventHandler",
    "broadcast_result",
    "validate_args",
    "require_ast_node",
    "handle_exceptions",
    "TrackEventHandler",
    "SceneEventHandler",
    "DeviceEventHandler",
    "ClipSlotEventHandler",
    "TransportEventHandler",
]
