"""
Device event handler for Ableton Live AST server.

Handles all device-related events including:
- Device added
- Device deleted
- Device parameter changes (with debouncing)
"""

import logging
from typing import Dict, Any

from ...ast import DeviceNode, NodeType, hash_tree
from ..ast_helpers import DiffGenerator
from ..constants import EventConstants, NodeIDPatterns, PlayingStatus
from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class DeviceEventHandler(BaseEventHandler):
    """
    Handler for device-related events.

    Manages device addition, deletion, and parameter changes.
    Uses debouncing for high-frequency parameter updates.
    """

    async def handle_device_added(self, args: list, seq_num: int) -> Dict[str, Any]:
        """
        Handle device added event.

        Args:
            args: [track_index, device_index, device_name]
            seq_num: Sequence number from event

        Returns:
            Dictionary with event result or None
        """
        if len(args) < 3:
            logger.warning(f"Invalid device added args: {args}")
            return None

        track_idx = int(args[0])
        device_idx = int(args[1])
        device_name = str(args[2])

        track_node = self._find_track(track_idx)
        if not track_node:
            logger.warning(f"Track {track_idx} not found in AST")
            return None

        # Create new device node using constants
        new_device = DeviceNode(
            name=device_name,
            device_type=EventConstants.DEFAULT_DEVICE_TYPE,
            id=NodeIDPatterns.device(track_idx, device_idx, seq_num)
        )

        # Insert device at the specified index
        devices_list = track_node.children
        if device_idx <= len(devices_list):
            devices_list.insert(device_idx, new_device)
        else:
            devices_list.append(new_device)

        hash_tree(track_node)
        self._recompute_parent_hashes(track_node)

        # Generate diff using DiffGenerator
        change = DiffGenerator.create_added_change(
            node_id=new_device.id,
            node_type='device',
            parent_id=track_node.id,
            path=f"tracks[{track_idx}].devices[{device_idx}]",
            new_value={'name': device_name},
            seq_num=seq_num
        )

        diff_result = DiffGenerator.create_diff_result(
            changes=[change],
            added=[new_device.id]
        )

        await self._broadcast_if_running(diff_result)

        logger.info(f"Device added to track {track_idx} at index {device_idx}: {device_name}")
        return {"type": "device_added", "track_idx": track_idx, "device_idx": device_idx, "name": device_name}

    async def handle_device_deleted(self, args: list, seq_num: int) -> Dict[str, Any]:
        """
        Handle device deleted event.

        Args:
            args: [track_index, device_index]
            seq_num: Sequence number from event

        Returns:
            Dictionary with event result or None
        """
        if len(args) < 2:
            logger.warning(f"Invalid device deleted args: {args}")
            return None

        track_idx = int(args[0])
        device_idx = int(args[1])

        # Find track node
        track_node = self._find_track(track_idx)
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
            await self._broadcast_if_running(diff_result)

            logger.info(f"Device removed from track {track_idx} at index {device_idx}")
            return {"type": "device_deleted", "track_idx": track_idx, "device_idx": device_idx}
        else:
            logger.warning(f"Device index {device_idx} out of range for track {track_idx}")
            return None

    async def handle_device_param(self, args: list, seq_num: int) -> Dict[str, Any]:
        """
        Handle device parameter change with debouncing.

        Uses the DebouncedBroadcaster for cleaner debouncing logic.

        Args:
            args: [track_index, device_index, parameter_index, parameter_value]
            seq_num: Sequence number from event

        Returns:
            Dictionary with event result or None
        """
        if len(args) < 4:
            return None

        track_idx = int(args[0])
        device_idx = int(args[1])
        param_idx = int(args[2])
        value = float(args[3])

        # Find device node
        track_node = self._find_track(track_idx)
        if not track_node:
            return None

        # Find device (naive device finding - assumes order)
        device_node = None
        devices = [c for c in track_node.children if c.node_type == NodeType.DEVICE]
        if device_idx < len(devices):
            device_node = devices[device_idx]

        if not device_node:
            return None

        # Update parameter in AST
        params = device_node.attributes.get('parameters', [])
        if param_idx < len(params):
            params[param_idx]['value'] = value
        else:
            # Expand list if needed
            while len(params) <= param_idx:
                params.append({'value': 0, 'name': 'Unknown'})
            params[param_idx]['value'] = value

        device_node.attributes['parameters'] = params

        # Create event arguments for debouncing
        event_args = {
            'track_index': track_idx,
            'device_index': device_idx,
            'parameter_index': param_idx,
            'parameter_value': value,
            'device_node_id': device_node.id,
            'seq_num': seq_num
        }

        # Use debouncer to handle high-frequency parameter changes
        await self.server.debouncer.debounce(
            "device_parameter_changed",
            event_args,
            self.broadcast_device_param_change
        )

        return {"type": "param_event", "track": track_idx, "device": device_idx, "param": param_idx, "value": value}

    async def broadcast_device_param_change(self, event_type: str, event_args: Dict[str, Any]) -> None:
        """
        Broadcast device parameter change after debouncing.

        Args:
            event_type: Event type (device_parameter_changed)
            event_args: Event arguments with parameter details
        """
        track_idx = event_args['track_index']
        device_idx = event_args['device_index']
        param_idx = event_args['parameter_index']
        value = event_args['parameter_value']
        node_id = event_args['device_node_id']
        seq_num = event_args.get('seq_num', 0)

        # Generate diff
        diff_result = {
            'changes': [{
                'type': 'state_changed',
                'node_id': node_id,
                'node_type': 'device',
                'path': f"tracks[{track_idx}].devices[{device_idx}].parameters[{param_idx}]",
                'attribute': 'value',
                'value': value,
                'param_index': param_idx,
                'new_value': value,
                'seq_num': seq_num
            }],
            'added': [],
            'removed': [],
            'modified': [node_id]
        }

        await self._broadcast_if_running(diff_result)

    def _recompute_parent_hashes(self, node):
        """Recompute hashes for parent nodes."""
        current = node
        while hasattr(current, 'parent') and current.parent:
            hash_tree(current.parent)
            current = current.parent
