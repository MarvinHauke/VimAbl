"""
Scene event handler for Ableton Live AST server.

Handles all scene-related events including:
- Scene rename
- Scene added
- Scene removed
- Scene reordered
"""

import json
import logging
import uuid
from typing import Dict, Any, List

from ...ast import NodeType, SceneNode, hash_tree
from ..ast_helpers import ASTNavigator, DiffGenerator, SceneIndexManager
from ..constants import NodeIDPatterns
from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class SceneEventHandler(BaseEventHandler):
    """
    Handler for scene-related events.

    Manages scene rename, addition, removal, and reordering operations.
    """

    async def handle_scene_renamed(self, args: list, seq_num: int) -> Dict[str, Any]:
        """
        Handle scene rename event.

        Args:
            args: [scene_index, new_name]
            seq_num: Sequence number from event

        Returns:
            Dictionary with event result or None
        """
        if len(args) < 2:
            logger.warning(f"Invalid scene rename args: {args}")
            return None

        scene_idx = int(args[0])
        new_name = str(args[1])

        # Find scene node by index
        scene_node = self._find_scene(scene_idx)
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
        await self._broadcast_if_running(diff_result)

        logger.info(f"Scene {scene_idx} renamed: '{old_name}' → '{new_name}'")
        return {"type": "scene_renamed", "scene_idx": scene_idx, "name": new_name}

    async def handle_scene_added(self, args: list, seq_num: int) -> Dict[str, Any]:
        """
        Handle scene added event.

        Args:
            args: [scene_index, scene_name]
            seq_num: Sequence number from event

        Returns:
            Dictionary with event result or None
        """
        logger.info(f"[handle_scene_added] Invoked with args: {args}, seq_num: {seq_num}")
        if len(args) < 2:
            logger.warning(f"[handle_scene_added] Invalid scene added args: {args}")
            return None

        scene_idx = int(args[0])
        scene_name = str(args[1])

        scenes = ASTNavigator.get_scenes(self.ast, cache=self.server.cache)
        current_scene_count = len(scenes)

        logger.info(f"[handle_scene_added] Current scene count: {current_scene_count}, adding scene at index {scene_idx}")
        logger.info(f"[handle_scene_added] Creating new scene: '{scene_name}' at index {scene_idx}")

        # Shift indices of subsequent scenes and clip slots
        changes = []
        modified_nodes = []

        scene_changes = SceneIndexManager.shift_scene_indices(self.ast, scene_idx, 1, seq_num)
        changes.extend(scene_changes)
        modified_nodes.extend([c['node_id'] for c in scene_changes])

        slot_changes = SceneIndexManager.shift_clip_slot_indices(self.ast, scene_idx, 1, seq_num)
        changes.extend(slot_changes)
        modified_nodes.extend([c['node_id'] for c in slot_changes])

        # Create new scene node
        new_scene = SceneNode(
            name=scene_name,
            index=scene_idx,
            id=NodeIDPatterns.scene(uuid.uuid4().hex[:8])
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
                parent_id=self.ast.id,
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

        logger.info(f"[handle_scene_added] Broadcasting diff_result: {json.dumps(diff_result, indent=2)}")
        await self._broadcast_if_running(diff_result)

        logger.info(f"Scene {scene_idx} added: '{scene_name}'")
        return {"type": "scene_added", "scene_idx": scene_idx, "name": scene_name}

    async def handle_scene_removed(self, args: list, seq_num: int) -> Dict[str, Any]:
        """
        Handle scene removed event.

        Args:
            args: [scene_index]
            seq_num: Sequence number from event

        Returns:
            Dictionary with event result or None
        """
        if len(args) < 1:
            return None

        scene_idx = int(args[0])
        scene_node = self._find_scene(scene_idx)

        if not scene_node:
            logger.warning(f"Scene {scene_idx} not found for removal")
            return None

        # Remove the scene node itself
        self.ast.remove_child(scene_node)

        # Initialize changes list with the scene removal
        changes = [
            DiffGenerator.create_removed_change(
                node_id=scene_node.id,
                node_type='scene',
                parent_id=self.ast.id,
                path=f"scenes[{scene_idx}]",
                value={'name': scene_node.attributes.get('name')},
                seq_num=seq_num
            )
        ]

        # Remove corresponding clip slots from all tracks
        removed_clip_slot_ids = self._remove_clip_slots_for_scene(scene_idx, seq_num, changes)

        # Shift indices of subsequent scenes and clip slots
        scene_changes = SceneIndexManager.shift_scene_indices(self.ast, scene_idx + 1, -1, seq_num)
        changes.extend(scene_changes)

        slot_changes = SceneIndexManager.shift_clip_slot_indices(self.ast, scene_idx + 1, -1, seq_num)
        changes.extend(slot_changes)

        # Recompute hashes after all modifications
        self._recompute_parent_hashes(self.ast)

        diff_result = DiffGenerator.create_diff_result(
            changes=changes,
            added=[],
            removed=[scene_node.id] + removed_clip_slot_ids,
            modified=[]
        )

        await self._broadcast_if_running(diff_result)

        logger.info(f"Scene {scene_idx} removed. Shifted indices for scenes > {scene_idx}.")
        return {"type": "scene_removed", "scene_idx": scene_idx}

    async def handle_scene_reordered(self, args: list, seq_num: int) -> Dict[str, Any]:
        """
        Handle scene reordered event.

        NOTE: Scene reorder events are IGNORED because:
        1. They cannot reliably identify which scene moved (scenes can have duplicate names)
        2. Our scene_added and scene_removed handlers already handle index shifting correctly
        3. Processing these events causes duplicate clip slots when scenes have empty/duplicate names

        The reorder events are sent by Ableton BEFORE scene_added, creating race conditions.

        Args:
            args: [new_index, scene_name]
            seq_num: Sequence number from event

        Returns:
            Dictionary indicating event was ignored
        """
        if len(args) < 2:
            return None

        new_idx = int(args[0])
        scene_name = str(args[1])

        logger.debug(f"Ignoring scene_reordered event: [{new_idx}, '{scene_name}'] - handled by scene_added/removed")

        # Return success without making changes
        return {"type": "scene_reordered", "scene_idx": new_idx, "ignored": True}

    def _insert_scene_at_index(self, new_scene: SceneNode, scene_idx: int) -> None:
        """
        Insert a scene at the specified index in the project children list.

        Args:
            new_scene: Scene node to insert
            scene_idx: Index where scene should be inserted
        """
        if not self.ast:
            logger.warning("No current AST, cannot insert scene.")
            return

        scenes = ASTNavigator.get_scenes(self.ast, cache=self.server.cache)
        tracks = ASTNavigator.get_tracks(self.ast, cache=self.server.cache)

        # Find the scene with index > scene_idx to insert before
        target_scene = None
        for s in self.ast.children:
            if s.node_type == NodeType.SCENE and s.attributes.get('index') > scene_idx:
                target_scene = s
                break

        if target_scene:
            insert_idx = self.ast.children.index(target_scene)
            self.ast.children.insert(insert_idx, new_scene)
            logger.debug(f"Inserted new scene at index {insert_idx}")
        elif scenes:
            # Append after last scene
            last_scene_idx = self.ast.children.index(scenes[-1])
            self.ast.children.insert(last_scene_idx + 1, new_scene)
            logger.debug(f"Appended after last scene (index {last_scene_idx + 1})")
        elif tracks:
            # No scenes, insert after last track
            last_track_idx = self.ast.children.index(tracks[-1])
            self.ast.children.insert(last_track_idx + 1, new_scene)
            logger.debug(f"Inserted after last track (index {last_track_idx + 1})")
        else:
            # Empty project
            self.ast.children.append(new_scene)
            logger.debug("Appended to empty children list")

    def _remove_clip_slots_for_scene(
        self,
        scene_idx: int,
        seq_num: int,
        changes: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Remove all clip slots for a given scene index.

        Args:
            scene_idx: Scene index to remove clip slots for
            seq_num: Sequence number from event
            changes: List to append removal changes to

        Returns:
            List of removed clip slot IDs
        """
        removed_clip_slot_ids = []
        tracks = ASTNavigator.get_tracks(self.ast)

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

    def _recompute_parent_hashes(self, node):
        """Recompute hashes for parent nodes."""
        current = node
        while hasattr(current, 'parent') and current.parent:
            hash_tree(current.parent)
            current = current.parent

    def _find_scene(self, scene_idx: int):
        """Find scene by index. Alias for consistency."""
        return ASTNavigator.find_scene_by_index(self.ast, scene_idx)
