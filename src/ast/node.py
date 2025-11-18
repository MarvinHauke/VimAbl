"""
AST Node class definitions for Ableton Live projects.

This module defines the node types that represent the structure of an Ableton Live project.
Each node type corresponds to a conceptual entity in the project (tracks, devices, clips, etc.).
"""

from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    """Enumeration of AST node types."""
    PROJECT = "project"
    TRACK = "track"
    DEVICE = "device"
    CLIP = "clip"
    CLIP_SLOT = "clip_slot"
    FILE_REF = "file_ref"
    SCENE = "scene"
    MIXER = "mixer"
    AUTOMATION = "automation"
    PARAMETER = "parameter"


@dataclass
class ASTNode:
    """
    Base class for all AST nodes.

    Each node represents a conceptual element in an Ableton Live project
    and maintains parent-child relationships for tree traversal.
    """
    node_type: NodeType
    id: Optional[str] = None
    parent: Optional['ASTNode'] = None
    children: List['ASTNode'] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    hash: Optional[str] = None  # Computed by hashing.py

    def add_child(self, child: 'ASTNode') -> None:
        """Add a child node and set its parent reference."""
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: 'ASTNode') -> None:
        """Remove a child node."""
        if child in self.children:
            child.parent = None
            self.children.remove(child)

    def get_path(self) -> List[str]:
        """Get the path from root to this node as a list of IDs."""
        path = []
        current = self
        while current is not None:
            if current.id:
                path.insert(0, current.id)
            current = current.parent
        return path

    def __repr__(self) -> str:
        return f"{self.node_type.value}(id={self.id}, children={len(self.children)})"


@dataclass
class ProjectNode(ASTNode):
    """Root node representing the entire Ableton Live project."""

    def __init__(self, **kwargs):
        super().__init__(node_type=NodeType.PROJECT, **kwargs)
        self.attributes['version'] = None
        self.attributes['creator'] = None


@dataclass
class TrackNode(ASTNode):
    """Node representing an audio or MIDI track."""

    def __init__(self, name: str, index: int, **kwargs):
        super().__init__(node_type=NodeType.TRACK, **kwargs)
        self.attributes['name'] = name
        self.attributes['index'] = index
        self.attributes['color'] = None
        self.attributes['is_muted'] = False
        self.attributes['is_soloed'] = False
        self.attributes['is_frozen'] = False


@dataclass
class DeviceNode(ASTNode):
    """Node representing a device (instrument or effect) on a track."""

    def __init__(self, name: str, device_type: str, **kwargs):
        super().__init__(node_type=NodeType.DEVICE, **kwargs)
        self.attributes['name'] = name
        self.attributes['device_type'] = device_type  # 'audio_effect', 'midi_effect', 'instrument'
        self.attributes['is_enabled'] = True


@dataclass
class ClipSlotNode(ASTNode):
    """Node representing a clip slot in the session view (track × scene grid)."""

    def __init__(self, track_index: int, scene_index: int, **kwargs):
        super().__init__(node_type=NodeType.CLIP_SLOT, **kwargs)
        self.attributes['track_index'] = track_index
        self.attributes['scene_index'] = scene_index
        self.attributes['has_clip'] = False
        self.attributes['has_stop_button'] = True
        self.attributes['playing_status'] = 0  # 0=stopped, 1=playing, 2=triggered
        self.attributes['color'] = None
        # Derived properties for convenience
        self.attributes['is_playing'] = False
        self.attributes['is_triggered'] = False


@dataclass
class ClipNode(ASTNode):
    """Node representing a MIDI or audio clip."""

    def __init__(self, name: str, clip_type: str, **kwargs):
        super().__init__(node_type=NodeType.CLIP, **kwargs)
        self.attributes['name'] = name
        self.attributes['clip_type'] = clip_type  # 'midi', 'audio'
        self.attributes['start_time'] = 0.0
        self.attributes['end_time'] = 0.0
        self.attributes['loop_start'] = 0.0
        self.attributes['loop_end'] = 0.0
        self.attributes['is_looped'] = True


@dataclass
class FileRefNode(ASTNode):
    """Node representing a reference to an external file (samples, etc.)."""

    def __init__(self, name: Optional[str], path: Optional[str], hash_val: Optional[str], ref_type: str, **kwargs):
        super().__init__(node_type=NodeType.FILE_REF, **kwargs)
        self.attributes['name'] = name
        self.attributes['path'] = path
        self.attributes['hash'] = hash_val
        self.attributes['ref_type'] = ref_type


@dataclass
class SceneNode(ASTNode):
    """Node representing a scene (horizontal row in session view)."""

    def __init__(self, name: str, index: int, **kwargs):
        super().__init__(node_type=NodeType.SCENE, **kwargs)
        self.attributes['name'] = name
        self.attributes['index'] = index
        self.attributes['tempo'] = None


@dataclass
class MixerNode(ASTNode):
    """Node representing mixer settings for a track."""

    def __init__(self, volume: float = 1.0, pan: float = 0.0, **kwargs):
        super().__init__(node_type=NodeType.MIXER, **kwargs)
        self.attributes['volume'] = volume
        self.attributes['pan'] = pan
        self.attributes['is_muted'] = False
        self.attributes['is_soloed'] = False


@dataclass
class ParameterNode(ASTNode):
    """Node representing an automatable parameter."""

    def __init__(self, name: str, value: Any, **kwargs):
        super().__init__(node_type=NodeType.PARAMETER, **kwargs)
        self.attributes['name'] = name
        self.attributes['value'] = value
        self.attributes['min'] = None
        self.attributes['max'] = None
        self.attributes['is_automated'] = False
