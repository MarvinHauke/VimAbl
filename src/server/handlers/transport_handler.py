"""
Transport event handler for Ableton Live AST server.

Handles all transport-related events including:
- Playback state (play/stop)
- Tempo changes
- Position changes
"""

import logging
from typing import Dict, Any

from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class TransportEventHandler(BaseEventHandler):
    """
    Handler for transport-related events.

    Manages transport state changes including playback, tempo,
    and position updates.

    Performance optimization (Phase 12a Task 3):
    - Tempo changes are debounced to reduce WebSocket message floods
    - Playback/position events are sent immediately (not debounced)
    """

    async def handle_transport_event(self, event_path: str, args: list, seq_num: int) -> Dict[str, Any]:
        """
        Handle transport events (updates Project attributes).

        Args:
            event_path: Full event path (e.g., "/live/transport/play")
            args: Event arguments
            seq_num: Sequence number from event

        Returns:
            Dictionary with event result or None
        """
        if not self.ast or len(args) < 1:
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

        old_value = self.ast.attributes.get(attribute)
        self.ast.attributes[attribute] = value

        # Phase 12a Task 3: Debounce tempo changes to reduce message floods
        if attribute == "tempo":
            event_args = {
                'node_id': self.ast.id,
                'attribute': attribute,
                'old_value': old_value,
                'new_value': value,
                'seq_num': seq_num
            }

            # Use debouncer for tempo (high-frequency during dragging)
            await self.server.debouncer.debounce(
                "tempo_changed",
                event_args,
                self.broadcast_transport_change
            )

            return {"type": "transport_event", "attribute": attribute, "value": value, "debounced": True}

        # Playback and position events are sent immediately (not debounced)
        diff_result = {
            'changes': [{
                'type': 'state_changed',
                'node_id': self.ast.id,
                'node_type': 'project',
                'path': "project",
                'attribute': attribute,
                'old_value': old_value,
                'new_value': value,
                'seq_num': seq_num
            }],
            'added': [],
            'removed': [],
            'modified': [self.ast.id]
        }

        await self._broadcast_if_running(diff_result)

        return {"type": "transport_event", "attribute": attribute, "value": value}

    async def broadcast_transport_change(self, event_type: str, event_args: Dict[str, Any]) -> None:
        """
        Broadcast transport change after debouncing (Phase 12a Task 3).

        Args:
            event_type: Event type (tempo_changed, etc.)
            event_args: Event arguments with transport details
        """
        diff_result = {
            'changes': [{
                'type': 'state_changed',
                'node_id': event_args['node_id'],
                'node_type': 'project',
                'path': "project",
                'attribute': event_args['attribute'],
                'old_value': event_args['old_value'],
                'new_value': event_args['new_value'],
                'seq_num': event_args.get('seq_num', 0)
            }],
            'added': [],
            'removed': [],
            'modified': [event_args['node_id']]
        }

        await self._broadcast_if_running(diff_result)
        logger.debug(f"Broadcasted debounced {event_type}: {event_args['new_value']}")
