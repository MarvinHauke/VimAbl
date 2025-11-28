"""
Base classes and decorators for event handlers.

This module provides the foundation for event handling including:
- EventResult: Standardized return type for handlers
- Decorators for validation, broadcasting, and error handling
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, List
from functools import wraps
import logging

from ..ast_helpers import ASTNode

logger = logging.getLogger(__name__)


@dataclass
class EventResult:
    """
    Standardized result from event handlers.

    Provides consistent structure for handler responses including
    diff generation, error reporting, and metadata tracking.
    """
    success: bool
    diff: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    modified_nodes: List[ASTNode] = field(default_factory=list)

    @classmethod
    def ok(cls, diff: Dict[str, Any] = None, **metadata) -> "EventResult":
        """Create a successful result."""
        return cls(success=True, diff=diff, metadata=metadata)

    @classmethod
    def error(cls, error_message: str, error_type: str = "handler_error", **metadata) -> "EventResult":
        """Create an error result."""
        return cls(success=False, error_message=error_message, error_type=error_type, metadata=metadata)

    def with_diff(self, diff: Dict[str, Any]) -> "EventResult":
        """Add diff to result (builder pattern)."""
        self.diff = diff
        return self

    def with_metadata(self, **metadata) -> "EventResult":
        """Add metadata to result (builder pattern)."""
        self.metadata.update(metadata)
        return self


def broadcast_result(func: Callable) -> Callable:
    """
    Decorator to automatically broadcast EventResult diff if successful.

    Expects the handler method to be on a class with:
    - websocket_server attribute
    - _broadcast_if_running() method
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        result = await func(self, *args, **kwargs)

        if isinstance(result, EventResult):
            if result.success and result.diff:
                await self._broadcast_if_running(result.diff)
            elif not result.success and result.error_message:
                await self._broadcast_error_if_running(
                    result.error_type or "handler_error",
                    result.error_message
                )

        return result

    return wrapper


def validate_args(*required_keys: str):
    """
    Decorator to validate that required arguments are present in event_args.

    Usage:
        @validate_args('track_index', 'device_index')
        async def handle_device_added(self, event_args):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, event_args: Dict[str, Any], *args, **kwargs):
            missing = [key for key in required_keys if key not in event_args]

            if missing:
                error_msg = f"Missing required arguments: {', '.join(missing)}"
                logger.error(f"{func.__name__}: {error_msg}")
                return EventResult.error(error_msg, error_type="validation_error")

            return await func(self, event_args, *args, **kwargs)

        return wrapper

    return decorator


def require_ast_node(node_finder: Callable):
    """
    Decorator to ensure an AST node exists before processing.

    Args:
        node_finder: Function that takes (self, event_args) and returns the node or None

    Usage:
        @require_ast_node(lambda self, args: self._find_track(args['track_index']))
        async def handle_track_event(self, event_args):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, event_args: Dict[str, Any], *args, **kwargs):
            node = node_finder(self, event_args)

            if node is None:
                error_msg = f"Required AST node not found for {func.__name__}"
                logger.error(error_msg)
                return EventResult.error(error_msg, error_type="node_not_found")

            return await func(self, event_args, *args, **kwargs)

        return wrapper

    return decorator


def handle_exceptions(func: Callable) -> Callable:
    """
    Decorator to catch and convert exceptions into EventResult errors.

    Prevents unhandled exceptions from crashing the event loop.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func.__name__}: {e}")
            return EventResult.error(
                str(e),
                error_type="exception",
                exception_type=type(e).__name__
            )

    return wrapper


class BaseEventHandler:
    """
    Base class for event handlers.

    Provides common functionality for all specialized handlers:
    - AST access
    - Broadcasting helpers
    - Node navigation utilities
    """

    def __init__(self, server):
        """
        Initialize handler with reference to main server.

        Args:
            server: ASTServer instance providing AST and broadcasting
        """
        self.server = server
        self.websocket_server = server.websocket_server
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def ast(self):
        """Get current AST from server."""
        return self.server.current_ast

    async def _broadcast_if_running(self, diff_result: Dict[str, Any]) -> None:
        """Broadcast diff result if WebSocket server is running."""
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_diff(diff_result)

    async def _broadcast_error_if_running(self, error_type: str, message: str) -> None:
        """Broadcast error if WebSocket server is running."""
        if self.websocket_server and self.websocket_server.is_running():
            await self.websocket_server.broadcast_error(error_type, message)

    def _find_track(self, track_index: int) -> Optional[ASTNode]:
        """Find track node by index."""
        from ..ast_helpers import ASTNavigator
        return ASTNavigator.find_track_by_index(self.ast, track_index)

    def _find_scene(self, scene_index: int) -> Optional[ASTNode]:
        """Find scene node by index."""
        from ..ast_helpers import ASTNavigator
        return ASTNavigator.find_scene_by_index(self.ast, scene_index)

    def _find_device(self, track_index: int, device_index: int) -> Optional[ASTNode]:
        """Find device node by track and device index."""
        from ..ast_helpers import ASTNavigator
        return ASTNavigator.find_device_by_indices(self.ast, track_index, device_index)
