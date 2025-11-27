"""
AST manipulation helpers for Ableton Live project ASTs.

This module provides utility classes for:
- Navigating AST nodes (finding tracks, scenes, etc.)
- Building AST node trees from raw parser data
- Managing hash computations
- Generating diff results
"""

import uuid
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path

from ..ast import (
    ASTNode,
    NodeType,
    ProjectNode,
    TrackNode,
    DeviceNode,
    ClipSlotNode,
    ClipNode,
    FileRefNode,
    SceneNode,
    MixerNode,
    hash_tree,
)


class ASTNavigator:
    """Helper class for finding nodes in the AST."""

    @staticmethod
    def find_track_by_index(root: ProjectNode, index: int) -> Optional[TrackNode]:
        """Find a track node by its index."""
        if not root:
            return None

        tracks = [child for child in root.children if child.node_type == NodeType.TRACK]

        for track in tracks:
            if track.attributes.get('index') == index:
                return track

        return None

    @staticmethod
    def find_scene_by_index(root: ProjectNode, index: int) -> Optional[SceneNode]:
        """Find a scene node by its index."""
        if not root:
            return None

        scenes = [child for child in root.children if child.node_type == NodeType.SCENE]

        for scene in scenes:
            if scene.attributes.get('index') == index:
                return scene

        return None

    @staticmethod
    def get_scenes(root: ProjectNode) -> List[SceneNode]:
        """Get all scene nodes from the project."""
        if not root:
            return []
        return [c for c in root.children if c.node_type == NodeType.SCENE]

    @staticmethod
    def get_tracks(root: ProjectNode) -> List[TrackNode]:
        """Get all track nodes from the project."""
        if not root:
            return []
        return [c for c in root.children if c.node_type == NodeType.TRACK]


class HashManager:
    """Helper class for managing hash computations."""

    @staticmethod
    def recompute_from_root(root: ProjectNode) -> None:
        """Recompute hashes for entire tree from root."""
        if root:
            hash_tree(root)

    @staticmethod
    def recompute_node_and_parents(node: ASTNode, root: ProjectNode) -> None:
        """
        Recompute hashes for a node and all its parents.

        Note: Since nodes don't have parent references, we rehash from root.
        This could be optimized with parent pointers in the future.
        """
        hash_tree(node)
        if root:
            hash_tree(root)


class DiffGenerator:
    """Helper class for generating standardized diff results."""

    @staticmethod
    def create_diff_result(
        changes: List[Dict[str, Any]],
        added: List[str] = None,
        removed: List[str] = None,
        modified: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a standardized diff result dictionary.

        Args:
            changes: List of change dictionaries
            added: List of added node IDs
            removed: List of removed node IDs
            modified: List of modified node IDs

        Returns:
            Standardized diff result dictionary
        """
        return {
            'changes': changes,
            'added': added or [],
            'removed': removed or [],
            'modified': modified or []
        }

    @staticmethod
    def create_modified_change(
        node_id: str,
        node_type: str,
        path: str,
        old_value: Dict[str, Any],
        new_value: Dict[str, Any],
        seq_num: int
    ) -> Dict[str, Any]:
        """Create a 'modified' change entry."""
        return {
            'type': 'modified',
            'node_id': node_id,
            'node_type': node_type,
            'path': path,
            'old_value': old_value,
            'new_value': new_value,
            'seq_num': seq_num
        }

    @staticmethod
    def create_added_change(
        node_id: str,
        node_type: str,
        parent_id: str,
        path: str,
        new_value: Dict[str, Any],
        seq_num: int
    ) -> Dict[str, Any]:
        """Create an 'added' change entry."""
        return {
            'type': 'added',
            'node_id': node_id,
            'node_type': node_type,
            'parent_id': parent_id,
            'path': path,
            'new_value': new_value,
            'seq_num': seq_num
        }

    @staticmethod
    def create_removed_change(
        node_id: str,
        node_type: str,
        parent_id: str,
        path: str,
        value: Dict[str, Any],
        seq_num: int
    ) -> Dict[str, Any]:
        """Create a 'removed' change entry."""
        return {
            'type': 'removed',
            'node_id': node_id,
            'node_type': node_type,
            'parent_id': parent_id,
            'path': path,
            'value': value,
            'seq_num': seq_num
        }

    @staticmethod
    def create_state_changed(
        node_id: str,
        node_type: str,
        path: str,
        attribute: str,
        old_value: Any,
        new_value: Any,
        seq_num: int
    ) -> Dict[str, Any]:
        """Create a 'state_changed' change entry."""
        return {
            'type': 'state_changed',
            'node_id': node_id,
            'node_type': node_type,
            'path': path,
            'attribute': attribute,
            'old_value': old_value,
            'new_value': new_value,
            'seq_num': seq_num
        }


class SceneIndexManager:
    """Helper class for managing scene and clip slot indices."""

    @staticmethod
    def shift_scene_indices(
        root: ProjectNode,
        start_idx: int,
        offset: int,
        seq_num: int
    ) -> List[Dict[str, Any]]:
        """
        Shift scene indices starting from start_idx by offset.

        Args:
            root: The project root node
            start_idx: Starting scene index to shift
            offset: Amount to shift (positive or negative)
            seq_num: Sequence number for tracking

        Returns:
            List of change dictionaries for shifted scenes
        """
        changes = []
        scenes = ASTNavigator.get_scenes(root)

        for scene in scenes:
            current_idx = scene.attributes.get('index', -1)
            if current_idx >= start_idx:
                new_idx = current_idx + offset
                scene.attributes['index'] = new_idx
                changes.append(
                    DiffGenerator.create_modified_change(
                        node_id=scene.id,
                        node_type='scene',
                        path=f"scenes[{current_idx}]",
                        old_value={'index': current_idx},
                        new_value={'index': new_idx},
                        seq_num=seq_num
                    )
                )

        return changes

    @staticmethod
    def shift_clip_slot_indices(
        root: ProjectNode,
        start_idx: int,
        offset: int,
        seq_num: int
    ) -> List[Dict[str, Any]]:
        """
        Shift clip slot scene indices starting from start_idx by offset.

        Args:
            root: The project root node
            start_idx: Starting scene index to shift
            offset: Amount to shift (positive or negative)
            seq_num: Sequence number for tracking

        Returns:
            List of change dictionaries for shifted clip slots
        """
        changes = []
        tracks = ASTNavigator.get_tracks(root)

        for track in tracks:
            for slot in track.children:
                if slot.node_type == NodeType.CLIP_SLOT:
                    current_slot_scene_idx = slot.attributes.get('scene_index', -1)
                    if current_slot_scene_idx >= start_idx:
                        new_slot_scene_idx = current_slot_scene_idx + offset
                        slot.attributes['scene_index'] = new_slot_scene_idx
                        changes.append(
                            DiffGenerator.create_modified_change(
                                node_id=slot.id,
                                node_type='clip_slot',
                                path=f"tracks[{track.attributes.get('index')}].clip_slots[{current_slot_scene_idx}]",
                                old_value={'scene_index': current_slot_scene_idx},
                                new_value={'scene_index': new_slot_scene_idx},
                                seq_num=seq_num
                            )
                        )

        return changes


class ASTBuilder:
    """Helper class for building AST node trees from raw parser data."""

    @staticmethod
    def build_node_tree(raw_ast: Dict, xml_root) -> ProjectNode:
        """
        Convert the raw dictionary AST to structured node objects.

        This bridges the gap between the parser's dict output
        and the AST node structure.
        """
        project = ProjectNode(id="project")

        # Add tracks with devices, clip slots, and clips
        ASTBuilder._build_tracks(project, raw_ast)

        # Add scenes
        ASTBuilder._build_scenes(project, raw_ast)

        # Add file references
        ASTBuilder._build_file_refs(project, raw_ast)

        return project

    @staticmethod
    def _build_tracks(project: ProjectNode, raw_ast: Dict) -> None:
        """Build track nodes and add them to the project."""
        for track_data in raw_ast.get("tracks", []):
            track_node = TrackNode(
                name=track_data["name"],
                index=track_data["index"],
                id=f"track_{track_data['index']}"
            )

            # Set track type (regular, return, or master)
            if track_data.get("type") is not None:
                track_node.attributes["type"] = track_data["type"]

            # Set color if available
            if track_data.get("color") is not None:
                track_node.attributes["color"] = track_data["color"]

            # Add devices
            ASTBuilder._build_devices(track_node, track_data)

            # Add clip slots
            ASTBuilder._build_clip_slots(track_node, track_data)

            # Add mixer settings
            ASTBuilder._build_mixer(track_node, track_data)

            project.add_child(track_node)

    @staticmethod
    def _build_devices(track_node: TrackNode, track_data: Dict) -> None:
        """Build device nodes and add them to the track."""
        for device_idx, device_data in enumerate(track_data.get("devices", [])):
            device_node = DeviceNode(
                name=device_data.get("name", "Unknown"),
                device_type=device_data.get("type", "unknown"),
                id=f"device_{track_data['index']}_{device_idx}"
            )
            device_node.attributes['is_enabled'] = device_data.get("is_enabled", True)
            device_node.attributes['plugin_info'] = device_data.get("plugin_info", {})
            device_node.attributes['parameters'] = device_data.get("parameters", [])

            track_node.add_child(device_node)

    @staticmethod
    def _build_clip_slots(track_node: TrackNode, track_data: Dict) -> None:
        """Build clip slot nodes and add them to the track."""
        for slot_data in track_data.get("clip_slots", []):
            scene_idx = slot_data["scene_index"]
            clip_slot_node = ClipSlotNode(
                track_index=track_data["index"],
                scene_index=scene_idx,
                id=f"clip_slot_{uuid.uuid4().hex[:8]}"
            )

            # Set clip slot properties
            clip_slot_node.attributes['has_clip'] = slot_data.get("has_clip", False)
            clip_slot_node.attributes['has_stop_button'] = slot_data.get("has_stop_button", True)
            clip_slot_node.attributes['color'] = slot_data.get("color")

            # If slot has a clip, add it as a child
            if slot_data.get("has_clip") and slot_data.get("clip"):
                clip_node = ASTBuilder._build_clip(slot_data["clip"], track_data["index"], scene_idx)
                clip_slot_node.add_child(clip_node)

            track_node.add_child(clip_slot_node)

    @staticmethod
    def _build_clip(clip_data: Dict, track_idx: int, scene_idx: int) -> ClipNode:
        """Build a clip node from clip data."""
        clip_node = ClipNode(
            name=clip_data.get("name", "Untitled"),
            clip_type=clip_data.get("type", "midi"),
            id=f"clip_{track_idx}_{scene_idx}"
        )
        clip_node.attributes['start_time'] = clip_data.get("start_time", 0.0)
        clip_node.attributes['end_time'] = clip_data.get("end_time", 0.0)
        clip_node.attributes['loop_start'] = clip_data.get("loop_start", 0.0)
        clip_node.attributes['loop_end'] = clip_data.get("loop_end", 0.0)
        clip_node.attributes['is_looped'] = clip_data.get("is_looped", True)
        clip_node.attributes['color'] = clip_data.get("color", -1)
        clip_node.attributes['view'] = clip_data.get("view", "session")

        # Add type-specific attributes
        if clip_data.get("type") == "midi":
            clip_node.attributes['note_count'] = clip_data.get("note_count", 0)
            clip_node.attributes['has_notes'] = clip_data.get("has_notes", False)
        elif clip_data.get("type") == "audio":
            clip_node.attributes['sample_name'] = clip_data.get("sample_name", "")
            clip_node.attributes['is_warped'] = clip_data.get("is_warped", False)
            clip_node.attributes['warp_mode'] = clip_data.get("warp_mode", "Unknown")

        return clip_node

    @staticmethod
    def _build_mixer(track_node: TrackNode, track_data: Dict) -> None:
        """Build mixer node and add it to the track."""
        mixer_data = track_data.get("mixer")
        if mixer_data:
            mixer_node = MixerNode(
                volume=mixer_data.get("volume", 1.0),
                pan=mixer_data.get("pan", 0.0),
                id=f"mixer_{track_data['index']}"
            )
            mixer_node.attributes['is_muted'] = mixer_data.get("is_muted", False)
            mixer_node.attributes['is_soloed'] = mixer_data.get("is_soloed", False)
            mixer_node.attributes['crossfader'] = mixer_data.get("crossfader", "None")
            mixer_node.attributes['sends'] = mixer_data.get("sends", [])

            track_node.add_child(mixer_node)

    @staticmethod
    def _build_scenes(project: ProjectNode, raw_ast: Dict) -> None:
        """Build scene nodes and add them to the project."""
        for scene_data in raw_ast.get("scenes", []):
            scene_node = SceneNode(
                name=scene_data.get("name", ""),
                index=scene_data.get("index", 0),
                id=f"scene_{uuid.uuid4().hex[:8]}"
            )
            scene_node.attributes['color'] = scene_data.get("color", -1)
            scene_node.attributes['tempo'] = scene_data.get("tempo", 120.0)
            scene_node.attributes['is_tempo_enabled'] = scene_data.get("is_tempo_enabled", False)
            scene_node.attributes['time_signature_id'] = scene_data.get("time_signature_id", 201)
            scene_node.attributes['is_time_signature_enabled'] = scene_data.get("is_time_signature_enabled", False)
            scene_node.attributes['annotation'] = scene_data.get("annotation", "")

            project.add_child(scene_node)

    @staticmethod
    def _build_file_refs(project: ProjectNode, raw_ast: Dict) -> None:
        """Build file reference nodes and add them to the project."""
        for i, ref_data in enumerate(raw_ast.get("file_refs", [])):
            hash_val = ref_data.get("hash")
            ref_id = f"fileref_{hash_val[:8]}" if hash_val else f"fileref_{i}"

            ref_node = FileRefNode(
                name=ref_data.get("name"),
                path=ref_data.get("path"),
                hash_val=hash_val,
                ref_type=ref_data.get("type", "Unknown"),
                id=ref_id
            )
            project.add_child(ref_node)
