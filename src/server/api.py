"""
API Server for querying and manipulating Ableton Live project ASTs.

This provides a programmatic interface for:
- Loading and parsing .als files
- Querying AST structure
- Finding specific nodes
- Computing diffs between versions
- WebSocket streaming of AST updates
- Future: LSP protocol implementation
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

from ..parser import load_ableton_xml, build_ast
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
    SerializationVisitor,
    DiffVisitor,
    SearchVisitor,
    hash_tree,
)


class ASTServer:
    """
    Server for managing Ableton Live project ASTs.

    Provides high-level operations for LSP-like functionality
    and WebSocket streaming.
    """

    def __init__(self, enable_websocket: bool = False, ws_host: str = "localhost", ws_port: int = 8765):
        self.current_ast: Optional[ASTNode] = None
        self.current_file: Optional[Path] = None
        self.serializer = SerializationVisitor()
        self.diff_visitor = DiffVisitor()
        self.search_visitor = SearchVisitor()

        # WebSocket server (optional)
        self.websocket_server: Optional[Any] = None
        self.enable_websocket = enable_websocket
        self.ws_host = ws_host
        self.ws_port = ws_port

        if enable_websocket:
            # Import here to avoid dependency if WebSocket is not used
            from ..websocket import ASTWebSocketServer
            self.websocket_server = ASTWebSocketServer(ws_host, ws_port)

    def load_project(self, file_path: Path, broadcast: bool = True) -> Dict[str, Any]:
        """
        Load an Ableton Live project file and build its AST.

        Args:
            file_path: Path to .als or .xml file
            broadcast: Whether to broadcast full AST to WebSocket clients (default: True)
                       Set to False if you're computing diffs manually

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

        # Broadcast to WebSocket clients if enabled
        if broadcast and self.websocket_server and self.websocket_server.is_running():
            asyncio.create_task(self.websocket_server.broadcast_full_ast(self.current_ast, str(file_path)))

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

        # Add tracks with devices, clip slots, and clips
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

            # Add clip slots to track (NEW: replaces old clip handling)
            for slot_data in track_data.get("clip_slots", []):
                scene_idx = slot_data["scene_index"]
                clip_slot_node = ClipSlotNode(
                    track_index=track_data["index"],
                    scene_index=scene_idx,
                    id=f"clip_slot_{track_data['index']}_{scene_idx}"
                )
                
                # Set clip slot properties
                clip_slot_node.attributes['has_clip'] = slot_data.get("has_clip", False)
                clip_slot_node.attributes['has_stop_button'] = slot_data.get("has_stop_button", True)
                clip_slot_node.attributes['color'] = slot_data.get("color")
                
                # If slot has a clip, add it as a child of the clip slot
                if slot_data.get("has_clip") and slot_data.get("clip"):
                    clip_data = slot_data["clip"]
                    clip_node = ClipNode(
                        name=clip_data.get("name", "Untitled"),
                        clip_type=clip_data.get("type", "midi"),
                        id=f"clip_{track_data['index']}_{scene_idx}"
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

                    clip_slot_node.add_child(clip_node)

                track_node.add_child(clip_slot_node)

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

    # WebSocket-related methods

    async def start_websocket_server(self) -> None:
        """Start the WebSocket server if enabled."""
        if self.websocket_server:
            await self.websocket_server.start()
            # Set the current AST if already loaded
            if self.current_ast:
                self.websocket_server.set_ast(self.current_ast)

    async def stop_websocket_server(self) -> None:
        """Stop the WebSocket server if running."""
        if self.websocket_server:
            await self.websocket_server.stop()

    async def broadcast_diff(self, diff_result: Dict[str, Any]) -> None:
        """
        Broadcast a diff to WebSocket clients.

        Args:
            diff_result: Diff result from DiffVisitor
        """
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)

    async def process_live_event(self, event_path: str, args: list, seq_num: int, timestamp: float) -> Optional[Dict[str, Any]]:
        """
        Process a real-time event from Ableton Live and update the AST.

        Maps OSC events to AST modifications, generates diffs, and broadcasts updates.

        Args:
            event_path: OSC event path (e.g., "/live/track/renamed")
            args: Event arguments
            seq_num: Sequence number from UDP
            timestamp: Event timestamp

        Returns:
            Dictionary with processing result, or None if event was ignored

        Event Types:
            - /live/track/renamed <track_idx> <name>
            - /live/track/mute <track_idx> <muted_bool>
            - /live/track/arm <track_idx> <armed_bool>
            - /live/track/volume <track_idx> <volume_float>
            - /live/device/added <track_idx> <device_idx> <name>
            - /live/device/deleted <track_idx> <device_idx>
            - /live/device/param <track_idx> <device_idx> <param_id> <value>
            - /live/scene/renamed <scene_idx> <name>
            - /live/transport/play <is_playing_bool>
            - /live/transport/tempo <bpm_float>
        """
        if not self.current_ast:
            logger.warning(f"No AST loaded, ignoring event: {event_path}")
            return None

        try:
            # Route event to appropriate handler
            if event_path == "/live/track/renamed":
                return await self._handle_track_renamed(args, seq_num)
            elif event_path == "/live/track/mute":
                return await self._handle_track_state(args, seq_num, "is_muted")
            elif event_path == "/live/track/arm":
                return await self._handle_track_state(args, seq_num, "is_armed")
            elif event_path == "/live/track/volume":
                return await self._handle_track_state(args, seq_num, "volume")
            elif event_path == "/live/device/added":
                return await self._handle_device_added(args, seq_num)
            elif event_path == "/live/device/deleted":
                return await self._handle_device_deleted(args, seq_num)
            elif event_path == "/live/scene/renamed":
                return await self._handle_scene_renamed(args, seq_num)
            elif event_path.startswith("/live/transport/"):
                # Transport events are lightweight, just broadcast without AST update
                return {"type": "transport_event", "broadcast_only": True}
            elif event_path.startswith("/live/device/param"):
                # Parameter changes are high-frequency, broadcast only
                return {"type": "param_event", "broadcast_only": True}
            else:
                logger.debug(f"Unhandled event type: {event_path}")
                return None

        except Exception as e:
            logger.error(f"Error processing event {event_path}: {e}", exc_info=True)
            if self.websocket_server and self.websocket_server.is_running():
                await self.websocket_server.broadcast_error(
                    "Event processing error",
                    f"Failed to process {event_path}: {str(e)}"
                )
            return None

    async def _handle_track_renamed(self, args: list, seq_num: int) -> Dict[str, Any]:
        """Handle track rename event."""
        if len(args) < 2:
            logger.warning(f"Invalid track rename args: {args}")
            return None

        track_idx = int(args[0])
        new_name = str(args[1])

        # Find track node by index
        track_node = self._find_track_by_index(track_idx)
        if not track_node:
            logger.warning(f"Track {track_idx} not found in AST")
            return None

        # Store old name for diff
        old_name = track_node.attributes.get('name', '')

        # Update track name
        track_node.attributes['name'] = new_name

        # Recompute hash for track and its parents
        hash_tree(track_node)
        self._recompute_parent_hashes(track_node)

        # Generate minimal diff
        diff_result = {
            'changes': [{
                'type': 'modified',
                'node_id': track_node.node_id,
                'node_type': 'track',
                'path': f"tracks[{track_idx}]",
                'old_value': {'name': old_name},
                'new_value': {'name': new_name},
                'seq_num': seq_num
            }],
            'added': [],
            'removed': [],
            'modified': [track_node.node_id]
        }

        # Broadcast diff
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)

        logger.info(f"Track {track_idx} renamed: '{old_name}' → '{new_name}'")
        return {"type": "track_renamed", "track_idx": track_idx, "name": new_name}

    async def _handle_track_state(self, args: list, seq_num: int, attribute: str) -> Dict[str, Any]:
        """Handle track state change (mute, arm, volume, etc.)."""
        if len(args) < 2:
            logger.warning(f"Invalid track state args: {args}")
            return None

        track_idx = int(args[0])
        value = args[1]

        # Find track node
        track_node = self._find_track_by_index(track_idx)
        if not track_node:
            logger.warning(f"Track {track_idx} not found in AST")
            return None

        # Store old value
        old_value = track_node.attributes.get(attribute)

        # Update attribute (lightweight, no rehash for state changes)
        track_node.attributes[attribute] = value

        # Generate minimal diff
        diff_result = {
            'changes': [{
                'type': 'state_changed',
                'node_id': track_node.node_id,
                'node_type': 'track',
                'path': f"tracks[{track_idx}]",
                'attribute': attribute,
                'old_value': old_value,
                'new_value': value,
                'seq_num': seq_num
            }],
            'added': [],
            'removed': [],
            'modified': [track_node.node_id]
        }

        # Broadcast diff
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)

        logger.info(f"Track {track_idx} {attribute} changed: {old_value} → {value}")
        return {"type": "track_state", "track_idx": track_idx, "attribute": attribute, "value": value}

    async def _handle_device_added(self, args: list, seq_num: int) -> Dict[str, Any]:
        """Handle device added event."""
        if len(args) < 3:
            logger.warning(f"Invalid device added args: {args}")
            return None

        track_idx = int(args[0])
        device_idx = int(args[1])
        device_name = str(args[2])

        # Find track node
        track_node = self._find_track_by_index(track_idx)
        if not track_node:
            logger.warning(f"Track {track_idx} not found in AST")
            return None

        # Create new device node
        new_device = DeviceNode(
            name=device_name,
            device_type='unknown',  # We don't know the type from UDP event
            node_id=f"device_{track_idx}_{device_idx}_{seq_num}"
        )

        # Insert device at the specified index
        # Find devices container or create if needed
        devices_list = track_node.children  # Devices are typically direct children
        if device_idx <= len(devices_list):
            devices_list.insert(device_idx, new_device)
        else:
            devices_list.append(new_device)

        # Recompute hashes
        hash_tree(track_node)
        self._recompute_parent_hashes(track_node)

        # Generate diff
        diff_result = {
            'changes': [{
                'type': 'added',
                'node_id': new_device.node_id,
                'node_type': 'device',
                'parent_id': track_node.node_id,
                'path': f"tracks[{track_idx}].devices[{device_idx}]",
                'value': {'name': device_name},
                'seq_num': seq_num
            }],
            'added': [new_device.node_id],
            'removed': [],
            'modified': []
        }

        # Broadcast diff
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)

        logger.info(f"Device added to track {track_idx} at index {device_idx}: {device_name}")
        return {"type": "device_added", "track_idx": track_idx, "device_idx": device_idx, "name": device_name}

    async def _handle_device_deleted(self, args: list, seq_num: int) -> Dict[str, Any]:
        """Handle device deleted event."""
        if len(args) < 2:
            logger.warning(f"Invalid device deleted args: {args}")
            return None

        track_idx = int(args[0])
        device_idx = int(args[1])

        # Find track node
        track_node = self._find_track_by_index(track_idx)
        if not track_node:
            logger.warning(f"Track {track_idx} not found in AST")
            return None

        # Find and remove device
        devices_list = track_node.children
        if device_idx < len(devices_list):
            removed_device = devices_list.pop(device_idx)
            
            # Recompute hashes
            hash_tree(track_node)
            self._recompute_parent_hashes(track_node)

            # Generate diff
            diff_result = {
                'changes': [{
                    'type': 'removed',
                    'node_id': removed_device.node_id,
                    'node_type': 'device',
                    'parent_id': track_node.node_id,
                    'path': f"tracks[{track_idx}].devices[{device_idx}]",
                    'value': {'name': removed_device.attributes.get('name', 'unknown')},
                    'seq_num': seq_num
                }],
                'added': [],
                'removed': [removed_device.node_id],
                'modified': []
            }

            # Broadcast diff
            if self.websocket_server and self.websocket_server.is_running():
                await self.websocket_server.broadcast_diff(diff_result)

            logger.info(f"Device removed from track {track_idx} at index {device_idx}")
            return {"type": "device_deleted", "track_idx": track_idx, "device_idx": device_idx}
        else:
            logger.warning(f"Device index {device_idx} out of range for track {track_idx}")
            return None

    async def _handle_scene_renamed(self, args: list, seq_num: int) -> Dict[str, Any]:
        """Handle scene rename event."""
        if len(args) < 2:
            logger.warning(f"Invalid scene rename args: {args}")
            return None

        scene_idx = int(args[0])
        new_name = str(args[1])

        # Find scene node by index
        scene_node = self._find_scene_by_index(scene_idx)
        if not scene_node:
            logger.warning(f"Scene {scene_idx} not found in AST")
            return None

        # Store old name
        old_name = scene_node.attributes.get('name', '')

        # Update scene name
        scene_node.attributes['name'] = new_name

        # Recompute hash
        hash_tree(scene_node)
        self._recompute_parent_hashes(scene_node)

        # Generate diff
        diff_result = {
            'changes': [{
                'type': 'modified',
                'node_id': scene_node.node_id,
                'node_type': 'scene',
                'path': f"scenes[{scene_idx}]",
                'old_value': {'name': old_name},
                'new_value': {'name': new_name},
                'seq_num': seq_num
            }],
            'added': [],
            'removed': [],
            'modified': [scene_node.node_id]
        }

        # Broadcast diff
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)

        logger.info(f"Scene {scene_idx} renamed: '{old_name}' → '{new_name}'")
        return {"type": "scene_renamed", "scene_idx": scene_idx, "name": new_name}

    def _find_track_by_index(self, index: int) -> Optional[TrackNode]:
        """Find a track node by its index."""
        if not self.current_ast:
            return None

        # Tracks are typically direct children of the project node
        tracks = [child for child in self.current_ast.children if child.node_type == NodeType.TRACK]
        
        for track in tracks:
            if track.attributes.get('index') == index:
                return track
        
        return None

    def _find_scene_by_index(self, index: int) -> Optional[SceneNode]:
        """Find a scene node by its index."""
        if not self.current_ast:
            return None

        # Scenes are typically direct children of the project node
        scenes = [child for child in self.current_ast.children if child.node_type == NodeType.SCENE]
        
        if index < len(scenes):
            return scenes[index]
        
        return None

    def _recompute_parent_hashes(self, node: ASTNode) -> None:
        """Recompute hashes for all parent nodes up to the root."""
        # Note: This assumes nodes have a parent reference or we traverse from root
        # Since our current AST doesn't have parent pointers, we rehash from root
        if self.current_ast:
            hash_tree(self.current_ast)

    def get_websocket_status(self) -> Dict[str, Any]:
        """
        Get WebSocket server status.

        Returns:
            Dictionary with server status info
        """
        if not self.websocket_server:
            return {
                "enabled": False,
                "running": False,
            }

        return {
            "enabled": True,
            "running": self.websocket_server.is_running(),
            "host": self.ws_host,
            "port": self.ws_port,
            "clients": self.websocket_server.get_client_count(),
        }
