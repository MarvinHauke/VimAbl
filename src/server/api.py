"""
API Server for querying and manipulating Ableton Live project ASTs.

This provides a programmatic interface for:
- Loading and parsing .als files
- Querying AST structure
- Finding specific nodes
- Computing diffs between versions
- Future: LSP protocol implementation
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..parser import load_ableton_xml, build_ast
from ..ast import (
    ASTNode,
    NodeType,
    ProjectNode,
    TrackNode,
    DeviceNode,
    ClipNode,
    FileRefNode,
    SceneNode,
    MixerNode,
    SerializationVisitor,
    DiffVisitor,
    SearchVisitor,
    hash_tree,
)


class ASTServer:
    """
    Server for managing Ableton Live project ASTs.

    Provides high-level operations for LSP-like functionality.
    """

    def __init__(self):
        self.current_ast: Optional[ASTNode] = None
        self.current_file: Optional[Path] = None
        self.serializer = SerializationVisitor()
        self.diff_visitor = DiffVisitor()
        self.search_visitor = SearchVisitor()

    def load_project(self, file_path: Path) -> Dict[str, Any]:
        """
        Load an Ableton Live project file and build its AST.

        Args:
            file_path: Path to .als or .xml file

        Returns:
            Dictionary with status and basic project info
        """
        self.current_file = file_path

        # Load and parse XML
        tree = load_ableton_xml(file_path)
        raw_ast = build_ast(tree.getroot())

        # Convert to structured AST nodes
        self.current_ast = self._build_node_tree(raw_ast, tree.getroot())

        # Compute hashes
        hash_tree(self.current_ast)

        return {
            "status": "success",
            "file": str(file_path),
            "root_hash": self.current_ast.hash,
        }

    def _build_node_tree(self, raw_ast: Dict, xml_root) -> ProjectNode:
        """
        Convert the raw dictionary AST to structured node objects.

        This bridges the gap between the parser's dict output
        and the AST node structure.
        """
        project = ProjectNode(id="project")

        # Add tracks with devices and clips
        for track_data in raw_ast.get("tracks", []):
            track_node = TrackNode(
                name=track_data["name"],
                index=track_data["index"],
                id=f"track_{track_data['index']}"
            )

            # Add devices to track
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

            # Add clips to track
            for clip_idx, clip_data in enumerate(track_data.get("clips", [])):
                clip_node = ClipNode(
                    name=clip_data.get("name", "Untitled"),
                    clip_type=clip_data.get("type", "midi"),
                    id=f"clip_{track_data['index']}_{clip_idx}"
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

                track_node.add_child(clip_node)

            # Add mixer settings to track
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

            project.add_child(track_node)

        # Add scenes
        for scene_data in raw_ast.get("scenes", []):
            scene_node = SceneNode(
                name=scene_data.get("name", ""),
                index=scene_data.get("index", 0),
                id=f"scene_{scene_data.get('index', 0)}"
            )
            scene_node.attributes['color'] = scene_data.get("color", -1)
            scene_node.attributes['tempo'] = scene_data.get("tempo", 120.0)
            scene_node.attributes['is_tempo_enabled'] = scene_data.get("is_tempo_enabled", False)
            scene_node.attributes['time_signature_id'] = scene_data.get("time_signature_id", 201)
            scene_node.attributes['is_time_signature_enabled'] = scene_data.get("is_time_signature_enabled", False)
            scene_node.attributes['annotation'] = scene_data.get("annotation", "")

            project.add_child(scene_node)

        # Add file references
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

        return project

    def get_ast_json(self, include_hash: bool = True) -> str:
        """
        Get the current AST as JSON.

        Args:
            include_hash: Whether to include node hashes

        Returns:
            JSON string representation
        """
        if not self.current_ast:
            raise RuntimeError("No project loaded")

        serializer = SerializationVisitor(include_hash=include_hash)
        return serializer.to_json(self.current_ast)

    def find_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a node by its ID.

        Args:
            node_id: The node ID to search for

        Returns:
            Serialized node or None if not found
        """
        if not self.current_ast:
            raise RuntimeError("No project loaded")

        node = self.search_visitor.find_by_id(self.current_ast, node_id)
        if node:
            return self.serializer.visit(node)
        return None

    def find_nodes_by_type(self, node_type_str: str) -> List[Dict[str, Any]]:
        """
        Find all nodes of a specific type.

        Args:
            node_type_str: Node type as string (e.g., "track", "device")

        Returns:
            List of serialized nodes
        """
        if not self.current_ast:
            raise RuntimeError("No project loaded")

        try:
            node_type = NodeType(node_type_str)
        except ValueError:
            return []

        nodes = self.search_visitor.find_by_type(self.current_ast, node_type)
        return [self.serializer.visit(node) for node in nodes]

    def diff_with_file(self, other_file: Path) -> List[Dict[str, Any]]:
        """
        Compute diff between current AST and another file.

        Args:
            other_file: Path to another .als or .xml file

        Returns:
            List of changes
        """
        if not self.current_ast:
            raise RuntimeError("No project loaded")

        # Load the other file
        tree = load_ableton_xml(other_file)
        raw_ast = build_ast(tree.getroot())
        other_ast = self._build_node_tree(raw_ast, tree.getroot())
        hash_tree(other_ast)

        # Compute diff
        return self.diff_visitor.diff(self.current_ast, other_ast)

    def get_project_info(self) -> Dict[str, Any]:
        """
        Get high-level information about the loaded project.

        Returns:
            Dictionary with project statistics
        """
        if not self.current_ast:
            raise RuntimeError("No project loaded")

        tracks = self.search_visitor.find_by_type(self.current_ast, NodeType.TRACK)
        devices = self.search_visitor.find_by_type(self.current_ast, NodeType.DEVICE)
        clips = self.search_visitor.find_by_type(self.current_ast, NodeType.CLIP)
        scenes = self.search_visitor.find_by_type(self.current_ast, NodeType.SCENE)
        file_refs = self.search_visitor.find_by_type(self.current_ast, NodeType.FILE_REF)

        return {
            "file": str(self.current_file) if self.current_file else None,
            "root_hash": self.current_ast.hash,
            "num_tracks": len(tracks),
            "num_devices": len(devices),
            "num_clips": len(clips),
            "num_scenes": len(scenes),
            "num_file_refs": len(file_refs),
            "track_names": [t.attributes.get("name") for t in tracks],
        }

    def query_nodes(self, predicate_str: str) -> List[Dict[str, Any]]:
        """
        Query nodes using a simple predicate.

        Example predicates:
        - "name == 'Audio'"
        - "index > 5"

        Args:
            predicate_str: Simple predicate expression

        Returns:
            List of matching nodes
        """
        if not self.current_ast:
            raise RuntimeError("No project loaded")

        # Simple predicate parser (can be expanded)
        # For now, just support attribute equality
        def predicate(node: ASTNode) -> bool:
            try:
                # Very basic evaluation - expand as needed
                if "==" in predicate_str:
                    key, value = predicate_str.split("==")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    return node.attributes.get(key) == value
                return False
            except Exception:
                return False

        nodes = self.search_visitor.find_by_predicate(self.current_ast, predicate)
        return [self.serializer.visit(node) for node in nodes]
