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
import uuid
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
from .ast_helpers import (
    ASTNavigator,
    ASTBuilder,
    HashManager,
    DiffGenerator,
    SceneIndexManager,
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
        
        # Event handler registry for routing events
        self._event_handlers = self._build_event_handler_registry()
    
    def _build_event_handler_registry(self) -> Dict[str, Any]:
        """
        Build the event handler registry for routing OSC events.
        
        Returns a dictionary mapping event paths to handler functions.
        """
        return {
            "/live/track/renamed": self._handle_track_renamed,
            "/live/track/mute": lambda args, seq: self._handle_track_state(args, seq, "is_muted"),
            "/live/track/arm": lambda args, seq: self._handle_track_state(args, seq, "is_armed"),
            "/live/track/volume": lambda args, seq: self._handle_track_state(args, seq, "volume"),
            "/live/device/added": self._handle_device_added,
            "/live/device/deleted": self._handle_device_deleted,
            "/live/scene/renamed": self._handle_scene_renamed,
            "/live/scene/added": self._handle_scene_added,
            "/live/scene/removed": self._handle_scene_removed,
            "/live/scene/reordered": self._handle_scene_reordered,
            "/live/clip_slot/created": self._handle_clip_slot_created,
        }

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
        return ASTBuilder.build_node_tree(raw_ast, xml_root)

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
        """
        if not self.current_ast:
            logger.warning(f"No AST loaded, ignoring event: {event_path}")
            return None

        try:
            # Try exact match first
            handler = self._event_handlers.get(event_path)
            
            if handler:
                return await handler(args, seq_num)
            
            # Handle prefix-based routing for transport and device params
            if event_path.startswith("/live/transport/"):
                return await self._handle_transport_event(event_path, args, seq_num)
            elif event_path.startswith("/live/device/param"):
                return await self._handle_device_param(args, seq_num)
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

        track_node = self._find_track_by_index(track_idx)
        if not track_node:
            logger.warning(f"Track {track_idx} not found in AST")
            return None

        old_name = track_node.attributes.get('name', '')
        track_node.attributes['name'] = new_name

        hash_tree(track_node)
        self._recompute_parent_hashes(track_node)

        change = DiffGenerator.create_modified_change(
            node_id=track_node.id,
            node_type='track',
            path=f"tracks[{track_idx}]",
            old_value={'name': old_name},
            new_value={'name': new_name},
            seq_num=seq_num
        )

        diff_result = DiffGenerator.create_diff_result(
            changes=[change],
            modified=[track_node.id]
        )

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

        track_node = self._find_track_by_index(track_idx)
        if not track_node:
            logger.warning(f"Track {track_idx} not found in AST")
            return None

        old_value = track_node.attributes.get(attribute)
        track_node.attributes[attribute] = value

        change = DiffGenerator.create_state_changed(
            node_id=track_node.id,
            node_type='track',
            path=f"tracks[{track_idx}]",
            attribute=attribute,
            old_value=old_value,
            new_value=value,
            seq_num=seq_num
        )

        diff_result = DiffGenerator.create_diff_result(
            changes=[change],
            modified=[track_node.id]
        )

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
            id=f"device_{track_idx}_{device_idx}_{seq_num}"
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
                'node_id': new_device.id,
                'node_type': 'device',
                'parent_id': track_node.id,
                'path': f"tracks[{track_idx}].devices[{device_idx}]",
                'new_value': {'name': device_name},
                'seq_num': seq_num
            }],
            'added': [new_device.id],
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
                    'node_id': removed_device.id,
                    'node_type': 'device',
                    'parent_id': track_node.id,
                    'path': f"tracks[{track_idx}].devices[{device_idx}]",
                    'value': {'name': removed_device.attributes.get('name', 'unknown')},
                    'seq_num': seq_num
                }],
                'added': [],
                'removed': [removed_device.id],
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
                'node_id': scene_node.id,
                'node_type': 'scene',
                'path': f"scenes[{scene_idx}]",
                'old_value': {'name': old_name},
                'new_value': {'name': new_name},
                'seq_num': seq_num
            }],
            'added': [],
            'removed': [],
            'modified': [scene_node.id]
        }

        # Broadcast diff
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)

        logger.info(f"Scene {scene_idx} renamed: '{old_name}' → '{new_name}'")
        return {"type": "scene_renamed", "scene_idx": scene_idx, "name": new_name}

    async def _handle_scene_added(self, args: list, seq_num: int) -> Dict[str, Any]:
        """Handle scene added event."""
        logger.info(f"[_handle_scene_added] Invoked with args: {args}, seq_num: {seq_num}")
        if len(args) < 2:
            logger.warning(f"[_handle_scene_added] Invalid scene added args: {args}")
            return None
            
        scene_idx = int(args[0])
        scene_name = str(args[1])

        scenes = ASTNavigator.get_scenes(self.current_ast)
        current_scene_count = len(scenes)

        logger.info(f"[_handle_scene_added] Current scene count: {current_scene_count}, adding scene at index {scene_idx}")
        logger.info(f"[_handle_scene_added] Creating new scene: '{scene_name}' at index {scene_idx}")

        # Shift indices of subsequent scenes and clip slots
        changes = []
        modified_nodes = []
        
        scene_changes = SceneIndexManager.shift_scene_indices(self.current_ast, scene_idx, 1, seq_num)
        changes.extend(scene_changes)
        modified_nodes.extend([c['node_id'] for c in scene_changes])
        
        slot_changes = SceneIndexManager.shift_clip_slot_indices(self.current_ast, scene_idx, 1, seq_num)
        changes.extend(slot_changes)
        modified_nodes.extend([c['node_id'] for c in slot_changes])

        # Create new scene node
        new_scene = SceneNode(
            name=scene_name,
            index=scene_idx,
            id=f"scene_{uuid.uuid4().hex[:8]}"
        )

        # Insert scene into project children
        self._insert_scene_at_index(new_scene, scene_idx)

        hash_tree(new_scene)
        self._recompute_parent_hashes(new_scene)

        # Add new scene change to list
        changes.append(
            DiffGenerator.create_added_change(
                node_id=new_scene.id,
                node_type='scene',
                parent_id=self.current_ast.id,
                path=f"scenes[{scene_idx}]",
                new_value={'name': scene_name, 'index': scene_idx},
                seq_num=seq_num
            )
        )

        diff_result = DiffGenerator.create_diff_result(
            changes=changes,
            added=[new_scene.id],
            removed=[],
            modified=modified_nodes
        )
        
        logger.info(f"[_handle_scene_added] Broadcasting diff_result: {json.dumps(diff_result, indent=2)}")
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)

        logger.info(f"Scene {scene_idx} added: '{scene_name}'")
        return {"type": "scene_added", "scene_idx": scene_idx, "name": scene_name}
    
    def _insert_scene_at_index(self, new_scene: SceneNode, scene_idx: int) -> None:
        """Insert a scene at the specified index in the project children list."""
        if not self.current_ast:
            logger.warning("No current AST, cannot insert scene.")
            return
        
        scenes = ASTNavigator.get_scenes(self.current_ast)
        tracks = ASTNavigator.get_tracks(self.current_ast)
        
        # Find the scene with index > scene_idx to insert before
        target_scene = None
        for s in self.current_ast.children:
            if s.node_type == NodeType.SCENE and s.attributes.get('index') > scene_idx:
                target_scene = s
                break
        
        if target_scene:
            insert_idx = self.current_ast.children.index(target_scene)
            self.current_ast.children.insert(insert_idx, new_scene)
            logger.debug(f"Inserted new scene at index {insert_idx}")
        elif scenes:
            # Append after last scene
            last_scene_idx = self.current_ast.children.index(scenes[-1])
            self.current_ast.children.insert(last_scene_idx + 1, new_scene)
            logger.debug(f"Appended after last scene (index {last_scene_idx + 1})")
        elif tracks:
            # No scenes, insert after last track
            last_track_idx = self.current_ast.children.index(tracks[-1])
            self.current_ast.children.insert(last_track_idx + 1, new_scene)
            logger.debug(f"Inserted after last track (index {last_track_idx + 1})")
        else:
            # Empty project
            self.current_ast.children.append(new_scene)
            logger.debug("Appended to empty children list")

    async def _handle_scene_removed(self, args: list, seq_num: int) -> Dict[str, Any]:
        """Handle scene removed event."""
        if len(args) < 1:
            return None
            
        scene_idx = int(args[0])
        scene_node = self._find_scene_by_index(scene_idx)
        
        if not scene_node:
            logger.warning(f"Scene {scene_idx} not found for removal")
            return None
            
        # Remove the scene node itself
        self.current_ast.remove_child(scene_node)
        
        # Initialize changes list with the scene removal
        changes = [
            DiffGenerator.create_removed_change(
                node_id=scene_node.id,
                node_type='scene',
                parent_id=self.current_ast.id,
                path=f"scenes[{scene_idx}]",
                value={'name': scene_node.attributes.get('name')},
                seq_num=seq_num
            )
        ]
        
        # Remove corresponding clip slots from all tracks
        removed_clip_slot_ids = self._remove_clip_slots_for_scene(scene_idx, seq_num, changes)

        # Shift indices of subsequent scenes and clip slots
        scene_changes = SceneIndexManager.shift_scene_indices(self.current_ast, scene_idx + 1, -1, seq_num)
        changes.extend(scene_changes)
        
        slot_changes = SceneIndexManager.shift_clip_slot_indices(self.current_ast, scene_idx + 1, -1, seq_num)
        changes.extend(slot_changes)

        # Recompute hashes after all modifications
        self._recompute_parent_hashes(self.current_ast)
        
        diff_result = DiffGenerator.create_diff_result(
            changes=changes,
            added=[],
            removed=[scene_node.id] + removed_clip_slot_ids,
            modified=[]
        )
        
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)
            
        logger.info(f"Scene {scene_idx} removed. Shifted indices for scenes > {scene_idx}.")
        return {"type": "scene_removed", "scene_idx": scene_idx}
    
    def _remove_clip_slots_for_scene(
        self, 
        scene_idx: int, 
        seq_num: int, 
        changes: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Remove all clip slots for a given scene index.
        
        Returns:
            List of removed clip slot IDs
        """
        removed_clip_slot_ids = []
        tracks = ASTNavigator.get_tracks(self.current_ast)
        
        for track in tracks:
            slots_to_remove = []
            for child in track.children:
                if (child.node_type == NodeType.CLIP_SLOT and 
                    child.attributes.get('scene_index') == scene_idx):
                    slots_to_remove.append(child)
            
            for slot in slots_to_remove:
                track.remove_child(slot)
                removed_clip_slot_ids.append(slot.id)
                
                changes.append(
                    DiffGenerator.create_removed_change(
                        node_id=slot.id,
                        node_type='clip_slot',
                        parent_id=track.id,
                        path=f"tracks[{track.attributes.get('index')}].clip_slots[{scene_idx}]",
                        value={},
                        seq_num=seq_num
                    )
                )
        
        return removed_clip_slot_ids

    async def _handle_scene_reordered(self, args: list, seq_num: int) -> Dict[str, Any]:
        """Handle scene reordered event.

        NOTE: Scene reorder events are IGNORED because:
        1. They cannot reliably identify which scene moved (scenes can have duplicate names)
        2. Our scene_added and scene_removed handlers already handle index shifting correctly
        3. Processing these events causes duplicate clip slots when scenes have empty/duplicate names

        The reorder events are sent by Ableton BEFORE scene_added, creating race conditions.
        """
        if len(args) < 2:
            return None

        new_idx = int(args[0])
        scene_name = str(args[1])

        logger.debug(f"Ignoring scene_reordered event: [{ new_idx}, '{scene_name}'] - handled by scene_added/removed")

        # Return success without making changes
        return {"type": "scene_reordered", "scene_idx": new_idx, "ignored": True}

    async def _handle_clip_slot_created(self, args: list, seq_num: int) -> Dict[str, Any]:
        """Handle clip slot created event."""
        logger.info(f"[_handle_clip_slot_created] Invoked with args: {args}, seq_num: {seq_num}")
        if len(args) < 5:
            logger.warning(f"[_handle_clip_slot_created] Invalid clip slot created args: {args}")
            return None
            
        track_idx = int(args[0])
        scene_idx = int(args[1])
        has_clip = bool(args[2])
        has_stop = bool(args[3])
        playing_status = int(args[4])
        
        track_node = self._find_track_by_index(track_idx)
        if not track_node:
            logger.warning(f"[_handle_clip_slot_created] Track {track_idx} not found for clip slot creation.")
            return None
            
        # Check for existing clip slot (deduplication)
        # Clip slots are identified by their scene_index attribute in our AST model
        existing_slot = None
        for child in track_node.children:
            if (child.node_type == NodeType.CLIP_SLOT and 
                child.attributes.get('scene_index') == scene_idx):
                existing_slot = child
                break
        
        if existing_slot:
            logger.info(f"[_handle_clip_slot_created] Clip slot [{track_idx},{scene_idx}] already exists, updating attributes.")
            # Update existing slot
            # We only need to update attributes if they changed, but for simplicity we update all
            # that might have come from the event
            existing_slot.attributes['has_clip'] = has_clip
            existing_slot.attributes['has_stop_button'] = has_stop
            existing_slot.attributes['playing_status'] = playing_status
            existing_slot.attributes['is_playing'] = (playing_status == 1)
            existing_slot.attributes['is_triggered'] = (playing_status == 2)
            
            hash_tree(existing_slot)
            self._recompute_parent_hashes(track_node)
            
            # Send 'modified' diff instead of 'added'
            diff_result = {
                'changes': [{
                    'type': 'modified',
                    'node_id': existing_slot.id,
                    'node_type': 'clip_slot',
                    'path': f"tracks[{track_idx}].clip_slots[{scene_idx}]",
                    'old_value': {}, # Not tracking old values for this dedupe
                    'new_value': {
                        'has_clip': has_clip,
                        'playing_status': playing_status
                    },
                    'seq_num': seq_num
                }],
                'added': [],
                'removed': [],
                'modified': [existing_slot.id]
            }
        else:
            logger.info(f"[_handle_clip_slot_created] Creating new clip slot: [{track_idx},{scene_idx}]")
            # Create new clip slot node
            new_slot = ClipSlotNode(
                track_index=track_idx,
                scene_index=scene_idx,
                id=f"clip_slot_{uuid.uuid4().hex[:8]}"
            )
            new_slot.attributes['has_clip'] = has_clip
            new_slot.attributes['has_stop_button'] = has_stop
            new_slot.attributes['playing_status'] = playing_status
            new_slot.attributes['is_playing'] = (playing_status == 1)
            new_slot.attributes['is_triggered'] = (playing_status == 2)
            
            # Insert in correct order (by scene_index)
            # Find correct position
            insert_pos = len(track_node.children)
            # Try to find insertion point among other clip slots
            clip_slots = [c for c in track_node.children if c.node_type == NodeType.CLIP_SLOT]
            for slot in clip_slots:
                if slot.attributes.get('scene_index') > scene_idx:
                    insert_pos = track_node.children.index(slot)
                    break
            
            if insert_pos < len(track_node.children):
                track_node.children.insert(insert_pos, new_slot)
                logger.debug(f"[_handle_clip_slot_created] Inserted new clip slot at index {insert_pos}")
            else:
                # If no slot with higher index, insert before mixer if possible, or at end
                # Usually clip slots are before mixer
                mixer_node = next((c for c in track_node.children if c.node_type == NodeType.MIXER), None)
                if mixer_node:
                    insert_pos = track_node.children.index(mixer_node)
                    track_node.children.insert(insert_pos, new_slot)
                    logger.debug(f"[_handle_clip_slot_created] Inserted new clip slot before mixer at index {insert_pos}")
                else:
                    track_node.children.append(new_slot)
                    logger.debug(f"[_handle_clip_slot_created] Appended new clip slot to track children")
            
            hash_tree(track_node)
            self._recompute_parent_hashes(track_node)
            
            diff_result = {
                'changes': [{
                    'type': 'added',
                    'node_id': new_slot.id,
                    'node_type': 'clip_slot',
                    'parent_id': track_node.id,
                    'path': f"tracks[{track_idx}].clip_slots[{scene_idx}]",
                    'new_value': {
                        'track_index': track_idx,
                        'scene_index': scene_idx,
                        'has_clip': has_clip,
                        'playing_status': playing_status
                    },
                    'seq_num': seq_num
                }],
                'added': [new_slot.id],
                'removed': [],
                'modified': []
            }
        
        logger.info(f"[_handle_clip_slot_created] Broadcasting diff_result: {json.dumps(diff_result, indent=2)}")
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)
            
        logger.info(f"Clip slot created for track {track_idx}, scene {scene_idx}")
        return {"type": "clip_slot_created", "track_idx": track_idx, "scene_idx": scene_idx}

    async def _handle_transport_event(self, event_path: str, args: list, seq_num: int) -> Dict[str, Any]:
        """Handle transport events (updates Project attributes)."""
        if not self.current_ast or len(args) < 1:
            return None
            
        attribute = ""
        value = args[0]
        
        if event_path == "/live/transport/play":
            attribute = "is_playing"
            value = bool(value)
        elif event_path == "/live/transport/tempo":
            attribute = "tempo"
            value = float(value)
        elif event_path == "/live/transport/position":
            attribute = "position"
            value = float(value)
            
        if not attribute:
            return None
            
        old_value = self.current_ast.attributes.get(attribute)
        self.current_ast.attributes[attribute] = value
        
        # Lightweight update (no rehash for transport)
        
        diff_result = {
            'changes': [{
                'type': 'state_changed',
                'node_id': self.current_ast.id,
                'node_type': 'project',
                'path': "project",
                'attribute': attribute,
                'old_value': old_value,
                'new_value': value,
                'seq_num': seq_num
            }],
            'added': [],
            'removed': [],
            'modified': [self.current_ast.id]
        }
        
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)
            
        return {"type": "transport_event", "attribute": attribute, "value": value}

    # Parameter update throttling
    _param_update_tasks = {}
    
    async def _handle_device_param(self, args: list, seq_num: int) -> Dict[str, Any]:
        """Handle device parameter change with debouncing."""
        if len(args) < 4:
            return None
            
        track_idx = int(args[0])
        device_idx = int(args[1])
        param_idx = int(args[2])
        value = float(args[3])
        
        # Find device node
        track_node = self._find_track_by_index(track_idx)
        if not track_node:
            return None
            
        # Naive device finding (assumes order)
        device_node = None
        devices = [c for c in track_node.children if c.node_type == NodeType.DEVICE]
        if device_idx < len(devices):
            device_node = devices[device_idx]
            
        if not device_node:
            return None
            
        # Update parameter in AST
        # Note: DeviceNode stores params in attributes['parameters'] list of dicts
        params = device_node.attributes.get('parameters', [])
        if param_idx < len(params):
            params[param_idx]['value'] = value
        else:
            # Expand list if needed (simple handling)
            while len(params) <= param_idx:
                params.append({'value': 0, 'name': 'Unknown'})
            params[param_idx]['value'] = value
        
        device_node.attributes['parameters'] = params
        
        # Debounced Broadcast
        # Use a tuple key for the parameter
        param_key = (track_idx, device_idx, param_idx)
        
        async def broadcast_later():
            await asyncio.sleep(0.1) # 100ms debounce
            
            # Check if we are the last task
            if self._param_update_tasks.get(param_key) == asyncio.current_task():
                # Generate and broadcast diff
                diff_result = {
                    'changes': [{
                        'type': 'state_changed',
                        'node_id': device_node.id,
                        'node_type': 'device',
                        'path': f"tracks[{track_idx}].devices[{device_idx}].parameters[{param_idx}]",
                        'attribute': 'value', # generic attribute name
                        'value': value, # simplified for frontend
                        'param_index': param_idx,
                        'new_value': value,
                        'seq_num': seq_num
                    }],
                    'added': [],
                    'removed': [],
                    'modified': [device_node.id]
                }
                if self.websocket_server and self.websocket_server.is_running():
                    await self.websocket_server.broadcast_diff(diff_result)
                
                del self._param_update_tasks[param_key]

        # Cancel existing task
        if param_key in self._param_update_tasks:
            self._param_update_tasks[param_key].cancel()
            
        # Schedule new task
        task = asyncio.create_task(broadcast_later())
        self._param_update_tasks[param_key] = task
        
        return {"type": "param_event", "track": track_idx, "device": device_idx, "param": param_idx, "value": value}

    def _find_track_by_index(self, index: int) -> Optional[TrackNode]:
        """Find a track node by its index."""
        return ASTNavigator.find_track_by_index(self.current_ast, index)

    def _find_scene_by_index(self, index: int) -> Optional[SceneNode]:
        """Find a scene node by its index."""
        return ASTNavigator.find_scene_by_index(self.current_ast, index)

    def _recompute_parent_hashes(self, node: ASTNode) -> None:
        """Recompute hashes for all parent nodes up to the root."""
        HashManager.recompute_node_and_parents(node, self.current_ast)

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
