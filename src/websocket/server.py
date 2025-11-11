"""WebSocket server for streaming AST updates to web clients."""

import asyncio
import json
import logging
from typing import Optional, Callable, Any, Dict
from websockets.server import serve, WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from .broadcaster import MessageBroadcaster
from .serializers import (
    create_full_ast_message,
    create_diff_message,
    create_error_message,
    create_ack_message,
)
from ..ast.node import ASTNode


logger = logging.getLogger(__name__)


class ASTWebSocketServer:
    """
    WebSocket server for streaming AST updates.

    Manages client connections and broadcasts AST data and updates
    to all connected clients.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Initialize the WebSocket server.

        Args:
            host: Host address to bind to
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self.broadcaster = MessageBroadcaster()
        self.server: Optional[Any] = None
        self._current_ast: Optional[ASTNode] = None
        self._project_path: Optional[str] = None
        self._on_client_message: Optional[Callable] = None
        self._running = False

    def set_ast(self, ast: ASTNode) -> None:
        """
        Set the current AST.

        Args:
            ast: The root AST node
        """
        self._current_ast = ast

    def set_message_handler(self, handler: Callable[[Dict[str, Any], WebSocketServerProtocol], None]) -> None:
        """
        Set a handler for client messages.

        Args:
            handler: Async function to handle client messages
        """
        self._on_client_message = handler

    async def start(self) -> None:
        """Start the WebSocket server."""
        if self._running:
            logger.warning("Server is already running")
            return

        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        self.server = await serve(
            self._handle_client,
            self.host,
            self.port,
        )
        self._running = True
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if not self._running:
            return

        logger.info("Stopping WebSocket server")
        self._running = False

        # Close all client connections
        await self.broadcaster.close_all()

        # Stop the server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("WebSocket server stopped")

    async def _handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """
        Handle a client connection.

        Args:
            websocket: WebSocket connection
        """
        # Register the client
        await self.broadcaster.register(websocket)

        try:
            # Send the current AST if available
            if self._current_ast:
                message = create_full_ast_message(self._current_ast, self._project_path)
                await self.broadcaster.send_to_client(websocket, message)
            else:
                # Send a message indicating no AST is loaded
                message = create_error_message(
                    "No AST loaded",
                    "The server has not loaded an AST yet. Please load a project."
                )
                await self.broadcaster.send_to_client(websocket, message)

            # Listen for messages from the client
            async for message_str in websocket:
                try:
                    message = json.loads(message_str)
                    logger.debug(f"Received message from client: {message.get('type')}")

                    # Handle the message
                    if self._on_client_message:
                        await self._on_client_message(message, websocket)
                    else:
                        # Default: just acknowledge
                        ack = create_ack_message(message.get('request_id'))
                        await self.broadcaster.send_to_client(websocket, ack)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from client: {e}")
                    error_msg = create_error_message("Invalid JSON", str(e))
                    await self.broadcaster.send_to_client(websocket, error_msg)
                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
                    error_msg = create_error_message("Server error", str(e))
                    await self.broadcaster.send_to_client(websocket, error_msg)

        except ConnectionClosed:
            logger.info("Client connection closed")
        except Exception as e:
            logger.error(f"Error in client handler: {e}")
        finally:
            # Unregister the client
            await self.broadcaster.unregister(websocket)

    async def broadcast_full_ast(self, ast: ASTNode, project_path: Optional[str] = None) -> None:
        """
        Broadcast the full AST to all clients.

        Args:
            ast: The root AST node
            project_path: Optional path to the project file
        """
        self._current_ast = ast
        if project_path:
            self._project_path = project_path
        message = create_full_ast_message(ast, self._project_path)
        await self.broadcaster.broadcast(message)
        logger.info("Broadcasted full AST to all clients")

    async def broadcast_diff(self, diff_result: Dict[str, Any]) -> None:
        """
        Broadcast an AST diff to all clients.

        Args:
            diff_result: Diff result from DiffVisitor
        """
        message = create_diff_message(diff_result)
        await self.broadcaster.broadcast(message)
        logger.info("Broadcasted diff to all clients")

    async def broadcast_error(self, error: str, details: Optional[str] = None) -> None:
        """
        Broadcast an error message to all clients.

        Args:
            error: Error message
            details: Optional error details
        """
        message = create_error_message(error, details)
        await self.broadcaster.broadcast(message)
        logger.warning(f"Broadcasted error: {error}")

    def get_client_count(self) -> int:
        """
        Get the number of connected clients.

        Returns:
            Number of connected clients
        """
        return self.broadcaster.get_client_count()

    def is_running(self) -> bool:
        """
        Check if the server is running.

        Returns:
            True if running, False otherwise
        """
        return self._running
