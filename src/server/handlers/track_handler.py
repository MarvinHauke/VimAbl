"""
Track event handler for Ableton Live AST server.

Handles all track-related events including:
- Track rename
- Track state changes (mute, arm, volume, pan, solo, etc.)
"""

import logging
from typing import Dict, Any, Optional

from ...ast import hash_tree
from ..ast_helpers import DiffGenerator
from .base import BaseEventHandler, EventResult

logger = logging.getLogger(__name__)


class TrackEventHandler(BaseEventHandler):
    """
    Handler for track-related events.

    Manages track rename and state changes (mute, arm, volume, etc.).
    """

    async def handle_track_renamed(self, args: list, seq_num: int) -> Dict[str, Any]:
        """
        Handle track rename event.

        Args:
            args: [track_index, new_name]
            seq_num: Sequence number from event

        Returns:
            Dictionary with event result or None
        """
        if len(args) < 2:
            logger.warning(f"Invalid track rename args: {args}")
            return None

        track_idx = int(args[0])
        new_name = str(args[1])

        # Find track node
        track_node = self._find_track(track_idx)
        if not track_node:
            logger.warning(f"Track {track_idx} not found in AST")
            return None

        # Update track name
        old_name = track_node.attributes.get('name', '')
        track_node.attributes['name'] = new_name

        # Update hashes
        hash_tree(track_node)
        self._recompute_parent_hashes(track_node)

        # Generate diff
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

        # Broadcast update
        await self._broadcast_if_running(diff_result)

        logger.info(f"Track {track_idx} renamed: '{old_name}' → '{new_name}'")
        return {"type": "track_renamed", "track_idx": track_idx, "name": new_name}

    async def handle_track_state(self, args: list, seq_num: int, attribute: str) -> Dict[str, Any]:
        """
        Handle track state change (mute, arm, volume, etc.).

        Args:
            args: [track_index, value]
            seq_num: Sequence number from event
            attribute: Attribute name (is_muted, is_armed, volume, etc.)

        Returns:
            Dictionary with event result or None
        """
        if len(args) < 2:
            logger.warning(f"Invalid track state args: {args}")
            return None

        track_idx = int(args[0])
        value = args[1]

        # Find track node
        track_node = self._find_track(track_idx)
        if not track_node:
            logger.warning(f"Track {track_idx} not found in AST")
            return None

        # Update track state
        old_value = track_node.attributes.get(attribute)
        track_node.attributes[attribute] = value

        # Generate diff
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

        # Broadcast update
        await self._broadcast_if_running(diff_result)

        logger.info(f"Track {track_idx} {attribute} changed: {old_value} → {value}")
        return {"type": "track_state", "track_idx": track_idx, "attribute": attribute, "value": value}

    def _recompute_parent_hashes(self, node):
        """Recompute hashes for parent nodes."""
        current = node
        while hasattr(current, 'parent') and current.parent:
            hash_tree(current.parent)
            current = current.parent
