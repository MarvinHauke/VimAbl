"""
Clip slot event handler for Ableton Live AST server.

Handles all clip slot-related events including:
- Clip slot created
- Clip slot changed
"""

import json
import logging
from typing import Dict, Any

from ...ast import hash_tree
from ..ast_helpers import DiffGenerator, ClipSlotManager
from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class ClipSlotEventHandler(BaseEventHandler):
    """
    Handler for clip slot-related events.

    Manages clip slot creation and updates, including deduplication
    of duplicate events from Ableton Live.
    """

    async def handle_clip_slot_created(self, args: list, seq_num: int) -> Dict[str, Any]:
        """
        Handle clip slot created event.

        Args:
            args: [track_index, scene_index, has_clip, has_stop, playing_status]
            seq_num: Sequence number from event

        Returns:
            Dictionary with event result or None
        """
        logger.info(f"[handle_clip_slot_created] Invoked with args: {args}, seq_num: {seq_num}")
        if len(args) < 5:
            logger.warning(f"[handle_clip_slot_created] Invalid clip slot created args: {args}")
            return None

        track_idx = int(args[0])
        scene_idx = int(args[1])
        has_clip = bool(args[2])
        has_stop = bool(args[3])
        playing_status = int(args[4])

        track_node = self._find_track(track_idx)
        if not track_node:
            logger.warning(f"[handle_clip_slot_created] Track {track_idx} not found for clip slot creation.")
            return None

        # Check for existing clip slot (deduplication)
        existing_slot = ClipSlotManager.find_existing_slot(track_node, scene_idx)

        if existing_slot:
            logger.info(f"[handle_clip_slot_created] Clip slot [{track_idx},{scene_idx}] already exists, updating attributes.")

            # Update existing slot attributes
            ClipSlotManager.update_clip_slot_attributes(
                existing_slot, has_clip, has_stop, playing_status
            )

            hash_tree(existing_slot)
            self._recompute_parent_hashes(track_node)

            # Send 'modified' diff instead of 'added'
            change = DiffGenerator.create_modified_change(
                node_id=existing_slot.id,
                node_type='clip_slot',
                path=f"tracks[{track_idx}].clip_slots[{scene_idx}]",
                old_value={},  # Not tracking old values for this dedupe
                new_value={'has_clip': has_clip, 'playing_status': playing_status},
                seq_num=seq_num
            )

            diff_result = DiffGenerator.create_diff_result(
                changes=[change],
                modified=[existing_slot.id]
            )
        else:
            logger.info(f"[handle_clip_slot_created] Creating new clip slot: [{track_idx},{scene_idx}]")

            # Create new clip slot node using ClipSlotManager
            new_slot = ClipSlotManager.create_clip_slot_node(
                track_idx=track_idx,
                scene_idx=scene_idx,
                has_clip=has_clip,
                has_stop=has_stop,
                playing_status=playing_status
            )

            # Insert clip slot in correct position
            ClipSlotManager.insert_clip_slot(track_node, new_slot, scene_idx)

            hash_tree(track_node)
            self._recompute_parent_hashes(track_node)

            # Generate diff for added clip slot
            change = DiffGenerator.create_added_change(
                node_id=new_slot.id,
                node_type='clip_slot',
                parent_id=track_node.id,
                path=f"tracks[{track_idx}].clip_slots[{scene_idx}]",
                new_value={
                    'track_index': track_idx,
                    'scene_index': scene_idx,
                    'has_clip': has_clip,
                    'playing_status': playing_status
                },
                seq_num=seq_num
            )

            diff_result = DiffGenerator.create_diff_result(
                changes=[change],
                added=[new_slot.id]
            )

        logger.info(f"[handle_clip_slot_created] Broadcasting diff_result: {json.dumps(diff_result, indent=2)}")
        await self._broadcast_if_running(diff_result)

        logger.info(f"Clip slot created for track {track_idx}, scene {scene_idx}")
        return {"type": "clip_slot_created", "track_idx": track_idx, "scene_idx": scene_idx}

    def _recompute_parent_hashes(self, node):
        """Recompute hashes for parent nodes."""
        current = node
        while hasattr(current, 'parent') and current.parent:
            hash_tree(current.parent)
            current = current.parent
