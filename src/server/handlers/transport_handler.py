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

        # Lightweight update (no rehash for transport)

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
