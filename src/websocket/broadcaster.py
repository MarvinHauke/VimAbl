"""Message broadcasting utility for WebSocket clients."""

import asyncio
import json
import logging
from typing import Any, Dict, Set
from websockets.server import WebSocketServerProtocol


logger = logging.getLogger(__name__)


class MessageBroadcaster:
    """Manages broadcasting messages to connected WebSocket clients."""

    def __init__(self):
        """Initialize the broadcaster."""
        self.clients: Set[WebSocketServerProtocol] = set()
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocketServerProtocol) -> None:
        """
        Register a new client.

        Args:
            websocket: WebSocket connection to register
        """
        async with self._lock:
            self.clients.add(websocket)
            logger.info(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket: WebSocketServerProtocol) -> None:
        """
        Unregister a client.

        Args:
            websocket: WebSocket connection to unregister
        """
        async with self._lock:
            self.clients.discard(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message dictionary to broadcast
        """
        if not self.clients:
            logger.debug("No clients connected, skipping broadcast")
            return

        # Convert message to JSON
        try:
            message_json = json.dumps(message)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize message: {e}")
            return

        # Send to all clients, removing any that fail
        disconnected = set()
        async with self._lock:
            for client in self.clients:
                try:
                    await client.send(message_json)
                    logger.debug(f"Sent message type '{message.get('type')}' to client")
                except Exception as e:
                    logger.warning(f"Failed to send to client: {e}")
                    disconnected.add(client)

            # Remove disconnected clients
            for client in disconnected:
                self.clients.discard(client)

        if disconnected:
            logger.info(f"Removed {len(disconnected)} disconnected clients")

    async def send_to_client(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]) -> None:
        """
        Send a message to a specific client.

        Args:
            websocket: Target WebSocket connection
            message: Message dictionary to send
        """
        try:
            message_json = json.dumps(message)
            await websocket.send(message_json)
            logger.debug(f"Sent message type '{message.get('type')}' to specific client")
        except Exception as e:
            logger.error(f"Failed to send to specific client: {e}")
            await self.unregister(websocket)

    def get_client_count(self) -> int:
        """
        Get the number of connected clients.

        Returns:
            Number of connected clients
        """
        return len(self.clients)

    async def close_all(self) -> None:
        """Close all client connections."""
        async with self._lock:
            for client in self.clients:
                try:
                    await client.close()
                except Exception as e:
                    logger.warning(f"Error closing client: {e}")
            self.clients.clear()
            logger.info("All clients disconnected")
