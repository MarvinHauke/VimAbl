"""Message broadcasting utility for WebSocket clients."""

import asyncio
import json
import logging
from typing import Any, Dict, Set, Optional
from websockets.server import WebSocketServerProtocol


logger = logging.getLogger(__name__)


class MessageBroadcaster:
    """
    Manages broadcasting messages to connected WebSocket clients.
    
    Uses a per-client queue and worker task pattern to ensure:
    1. Non-blocking broadcast (UDP listener is never blocked)
    2. Strict message ordering (messages are sent sequentially)
    3. Backpressure handling (slow clients don't consume infinite memory)
    """

    def __init__(self):
        """Initialize the broadcaster."""
        # Map websocket -> (queue, worker_task)
        self.clients: Dict[WebSocketServerProtocol, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocketServerProtocol) -> None:
        """
        Register a new client and start its sender worker.

        Args:
            websocket: WebSocket connection to register
        """
        async with self._lock:
            if websocket not in self.clients:
                # Create a bounded queue for backpressure
                # If queue fills up, we'll drop messages or disconnect
                queue = asyncio.Queue(maxsize=1000)
                
                # Start worker task
                task = asyncio.create_task(self._client_sender_loop(websocket, queue))
                
                self.clients[websocket] = {
                    'queue': queue,
                    'task': task
                }
                logger.info(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket: WebSocketServerProtocol) -> None:
        """
        Unregister a client and stop its worker.

        Args:
            websocket: WebSocket connection to unregister
        """
        async with self._lock:
            if websocket in self.clients:
                client_data = self.clients.pop(websocket)
                
                # Cancel worker task
                task = client_data['task']
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients.
        
        This method is non-blocking. It simply pushes the message to each
        client's queue. Actual sending happens in the background worker.

        Args:
            message: Message dictionary to broadcast
        """
        # Snapshot clients keys to avoid runtime error if dict changes during iteration
        # We don't need the lock for the whole loop, just to get the list of queues
        async with self._lock:
            if not self.clients:
                return
            # Get list of queues to push to
            queues = [data['queue'] for data in self.clients.values()]

        # Convert message to JSON once
        try:
            message_json = json.dumps(message)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize message: {e}")
            return

        # Push to all queues (non-blocking)
        for q in queues:
            try:
                # If queue is full, we drop the message for this client
                # This prevents slow clients from causing OOM on server
                q.put_nowait(message_json)
            except asyncio.QueueFull:
                logger.warning("Client queue full, dropping message")

    async def _client_sender_loop(self, websocket: WebSocketServerProtocol, queue: asyncio.Queue):
        """
        Background task to send messages to a specific client sequentially.
        """
        try:
            while True:
                # Get next message
                message_json = await queue.get()
                
                try:
                    await websocket.send(message_json)
                except Exception as e:
                    logger.warning(f"Failed to send to client: {e}")
                    # Verify connection is closed
                    await self.unregister(websocket)
                    break
                    
                queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in client sender loop: {e}")
            await self.unregister(websocket)

    async def send_to_client(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]) -> None:
        """
        Send a message to a specific client.

        Args:
            websocket: Target WebSocket connection
            message: Message dictionary to send
        """
        # Convert message to JSON
        try:
            message_json = json.dumps(message)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize message: {e}")
            return

        async with self._lock:
            if websocket in self.clients:
                queue = self.clients[websocket]['queue']
                try:
                    queue.put_nowait(message_json)
                except asyncio.QueueFull:
                    logger.warning("Client queue full, dropping specific message")

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
            # Get all websockets first
            websockets = list(self.clients.keys())
            
        # Unregister all (this cancels tasks)
        for ws in websockets:
            await self.unregister(ws)
            try:
                await ws.close()
            except Exception:
                pass
        
        logger.info("All clients disconnected")
