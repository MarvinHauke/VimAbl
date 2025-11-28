import pytest
from unittest.mock import MagicMock, AsyncMock
from src.server.handlers.transport_handler import TransportEventHandler
from src.ast import ProjectNode, NodeType

class MockServer:
    def __init__(self):
        self.current_ast = ProjectNode()
        self.current_ast.id = "project-root"
        self.websocket_server = MagicMock()
        self.websocket_server.is_running.return_value = True
        self.websocket_server.broadcast_diff = AsyncMock()
        self.websocket_server.broadcast_error = AsyncMock()
        # Phase 12a Task 3: Add debouncer mock for tempo debouncing
        self.debouncer = MagicMock()
        self.debouncer.debounce = AsyncMock()

@pytest.fixture
def server():
    return MockServer()

@pytest.fixture
def handler(server):
    return TransportEventHandler(server)

@pytest.mark.asyncio
async def test_handle_transport_event_play(handler, server):
    """
    Test handle_transport_event for play event.
    """
    args = [True] # is_playing
    result = await handler.handle_transport_event("/live/transport/play", args, seq_num=1)

    assert result is not None
    assert result["type"] == "transport_event"
    assert result["attribute"] == "is_playing"
    assert result["value"] is True
    
    # Verify AST update
    assert server.current_ast.attributes["is_playing"] is True
    
    # Verify broadcast
    server.websocket_server.broadcast_diff.assert_called_once()
    diff_result = server.websocket_server.broadcast_diff.call_args[0][0]
    assert len(diff_result["changes"]) == 1
    assert diff_result["changes"][0]["type"] == "state_changed"
    assert diff_result["changes"][0]["attribute"] == "is_playing"
    assert diff_result["changes"][0]["new_value"] is True

@pytest.mark.asyncio
async def test_handle_transport_event_tempo(handler, server):
    """
    Test handle_transport_event for tempo event.
    Phase 12a Task 3: Tempo should be debounced (not broadcast immediately).
    """
    args = [120.0]
    result = await handler.handle_transport_event("/live/transport/tempo", args, seq_num=2)

    assert result is not None
    assert result["attribute"] == "tempo"
    assert result["value"] == 120.0
    assert result["debounced"] is True  # Phase 12a: Tempo is debounced

    # Verify AST update (tempo is updated in AST immediately)
    assert server.current_ast.attributes["tempo"] == 120.0

    # Verify debouncer was called (Phase 12a Task 3)
    server.debouncer.debounce.assert_called_once()
    call_args = server.debouncer.debounce.call_args
    assert call_args[0][0] == "tempo_changed"  # event key
    assert call_args[0][1]["attribute"] == "tempo"  # event args
    assert call_args[0][1]["new_value"] == 120.0

    # Broadcast should NOT be called immediately (debounced)
    server.websocket_server.broadcast_diff.assert_not_called()

@pytest.mark.asyncio
async def test_handle_transport_event_position(handler, server):
    """
    Test handle_transport_event for position event.
    """
    args = [4.0]
    result = await handler.handle_transport_event("/live/transport/position", args, seq_num=3)

    assert result is not None
    assert result["attribute"] == "position"
    assert result["value"] == 4.0
    
    # Verify AST update
    assert server.current_ast.attributes["position"] == 4.0

@pytest.mark.asyncio
async def test_handle_transport_event_unknown(handler, server):
    """
    Test handle_transport_event for unknown transport event.
    """
    args = [1]
    result = await handler.handle_transport_event("/live/transport/unknown", args, seq_num=1)

    assert result is None

@pytest.mark.asyncio
async def test_handle_transport_event_no_ast(handler, server):
    """
    Test handle_transport_event when no AST is loaded.
    """
    server.current_ast = None
    args = [True]
    result = await handler.handle_transport_event("/live/transport/play", args, seq_num=1)

    assert result is None
