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
    ClipSlotManager,
)
from .constants import EventConstants, NodeIDPatterns, PlayingStatus
from .handlers import (
    EventResult,
    broadcast_result,
    validate_args,
    handle_exceptions,
    TrackEventHandler,
    SceneEventHandler,
    DeviceEventHandler,
    ClipSlotEventHandler,
    TransportEventHandler,
)
from .validation import validate_event_args, validate_required_keys, safe_get
from .utils import DebouncedBroadcaster
from .services import QueryService, ProjectService


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

        # Debouncer for high-frequency events (device params, tempo, etc.)
        self.debouncer = DebouncedBroadcaster(delay=EventConstants.DEBOUNCE_DELAY_SECONDS)

        # Initialize services
        self.query_service = QueryService(self)
        self.project_service = ProjectService(self)

        # Initialize specialized event handlers
        self.track_handler = TrackEventHandler(self)
        self.scene_handler = SceneEventHandler(self)
        self.device_handler = DeviceEventHandler(self)
        self.clip_slot_handler = ClipSlotEventHandler(self)
        self.transport_handler = TransportEventHandler(self)

        # Event handler registry for routing events
        self._event_handlers = self._build_event_handler_registry()
    
    def _build_event_handler_registry(self) -> Dict[str, Any]:
        """
        Build the event handler registry for routing OSC events.

        Uses specialized handler classes for different event domains.

        Returns a dictionary mapping event paths to handler functions.
        """
        return {
            # Track events
            "/live/track/renamed": self.track_handler.handle_track_renamed,
            "/live/track/mute": lambda args, seq: self.track_handler.handle_track_state(args, seq, "is_muted"),
            "/live/track/arm": lambda args, seq: self.track_handler.handle_track_state(args, seq, "is_armed"),
            "/live/track/volume": lambda args, seq: self.track_handler.handle_track_state(args, seq, "volume"),

            # Device events
            "/live/device/added": self.device_handler.handle_device_added,
            "/live/device/deleted": self.device_handler.handle_device_deleted,

            # Scene events
            "/live/scene/renamed": self.scene_handler.handle_scene_renamed,
            "/live/scene/added": self.scene_handler.handle_scene_added,
            "/live/scene/removed": self.scene_handler.handle_scene_removed,
            "/live/scene/reordered": self.scene_handler.handle_scene_reordered,

            # Clip slot events
            "/live/clip_slot/created": self.clip_slot_handler.handle_clip_slot_created,
        }

    async def _broadcast_if_running(self, diff_result: Dict[str, Any]) -> None:
        """
        Broadcast diff result if WebSocket server is running.

        Args:
            diff_result: Diff result dictionary to broadcast
        """
        await self._broadcast_if_running(diff_result)

    async def _broadcast_error_if_running(self, error_type: str, message: str) -> None:
        """
        Broadcast error if WebSocket server is running.

        Args:
            error_type: Type/category of the error
            message: Error message to broadcast
        """
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_error(error_type, message)

    def load_project(self, file_path: Path, broadcast: bool = True) -> Dict[str, Any]:
        """
        Load an Ableton Live project file and build its AST.

        Delegates to ProjectService.

        Args:
            file_path: Path to .als or .xml file
            broadcast: Whether to broadcast full AST to WebSocket clients (default: True)

        Returns:
            Dictionary with status and basic project info
        """
        return self.project_service.load_project(file_path, broadcast)

    def get_ast_json(self, include_hash: bool = True) -> str:
        """
        Get the current AST as JSON.

        Delegates to QueryService.

        Args:
            include_hash: Whether to include node hashes

        Returns:
            JSON string representation
        """
        return self.query_service.get_ast_json(include_hash)

    def find_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a node by its ID.

        Delegates to QueryService.

        Args:
            node_id: The node ID to search for

        Returns:
            Serialized node or None if not found
        """
        return self.query_service.find_node_by_id(node_id)

    def find_nodes_by_type(self, node_type_str: str) -> List[Dict[str, Any]]:
        """
        Find all nodes of a specific type.

        Delegates to QueryService.

        Args:
            node_type_str: Node type as string (e.g., "track", "device")

        Returns:
            List of serialized nodes
        """
        return self.query_service.find_nodes_by_type(node_type_str)

    def diff_with_file(self, other_file: Path) -> List[Dict[str, Any]]:
        """
        Compute diff between current AST and another file.

        Delegates to QueryService.

        Args:
            other_file: Path to another .als or .xml file

        Returns:
            List of changes
        """
        return self.query_service.diff_with_file(other_file)

    def get_project_info(self) -> Dict[str, Any]:
        """
        Get high-level information about the loaded project.

        Delegates to QueryService.

        Returns:
            Dictionary with project statistics
        """
        return self.query_service.get_project_info()

    def query_nodes(self, predicate_str: str) -> List[Dict[str, Any]]:
        """
        Query nodes using a simple predicate.

        Delegates to QueryService.

        Example predicates:
        - "name == 'Audio'"
        - "index > 5"

        Args:
            predicate_str: Simple predicate expression

        Returns:
            List of matching nodes
        """
        return self.query_service.query_nodes(predicate_str)

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
        await self._broadcast_if_running(diff_result)

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
                return await self.transport_handler.handle_transport_event(event_path, args, seq_num)
            elif event_path.startswith("/live/device/param"):
                return await self.device_handler.handle_device_param(args, seq_num)
            else:
                logger.debug(f"Unhandled event type: {event_path}")
                return None

        except Exception as e:
            logger.error(f"Error processing event {event_path}: {e}", exc_info=True)
            await self._broadcast_error_if_running(
                "Event processing error",
                f"Failed to process {event_path}: {str(e)}"
            )
            return None

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
