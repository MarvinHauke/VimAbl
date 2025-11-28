import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.server.api import ASTServer
from src.ast import ProjectNode

@pytest.fixture
def server():
    with patch("src.websocket.ASTWebSocketServer"), \
         patch("src.server.api.DebouncedBroadcaster"):
        server = ASTServer(enable_websocket=True)
        server.websocket_server = MagicMock()
        server.websocket_server.is_running.return_value = True
        server.websocket_server.broadcast_error = AsyncMock()
        return server

def test_initialization(server):
    """
    Test ASTServer initialization.
    """
    assert server.query_service is not None
    assert server.project_service is not None
    assert server.track_handler is not None
    assert server.scene_handler is not None
    assert server.device_handler is not None
    assert server.clip_slot_handler is not None
    assert server.transport_handler is not None
    assert server._event_handlers is not None

def test_service_delegation_load_project(server):
    """
    Test delegation of load_project to ProjectService.
    """
    server.project_service.load_project = MagicMock(return_value={"status": "success"})
    result = server.load_project("test.als", broadcast=False)
    server.project_service.load_project.assert_called_once_with("test.als", False)
    assert result["status"] == "success"

def test_service_delegation_get_ast_json(server):
    """
    Test delegation of get_ast_json to QueryService.
    """
    server.query_service.get_ast_json = MagicMock(return_value="{}")
    result = server.get_ast_json(include_hash=True)
    server.query_service.get_ast_json.assert_called_once_with(True)
    assert result == "{}"

def test_service_delegation_find_node_by_id(server):
    """
    Test delegation of find_node_by_id to QueryService.
    """
    server.query_service.find_node_by_id = MagicMock(return_value={"id": "1"})
    result = server.find_node_by_id("1")
    server.query_service.find_node_by_id.assert_called_once_with("1")
    assert result["id"] == "1"

def test_service_delegation_find_nodes_by_type(server):
    """
    Test delegation of find_nodes_by_type to QueryService.
    """
    server.query_service.find_nodes_by_type = MagicMock(return_value=[])
    result = server.find_nodes_by_type("track")
    server.query_service.find_nodes_by_type.assert_called_once_with("track")
    assert result == []

def test_service_delegation_query_nodes(server):
    """
    Test delegation of query_nodes to QueryService.
    """
    server.query_service.query_nodes = MagicMock(return_value=[])
    result = server.query_nodes("index > 0")
    server.query_service.query_nodes.assert_called_once_with("index > 0")
    assert result == []

def test_service_delegation_diff_with_file(server):
    """
    Test delegation of diff_with_file to QueryService.
    """
    server.query_service.diff_with_file = MagicMock(return_value=[])
    result = server.diff_with_file("other.als")
    server.query_service.diff_with_file.assert_called_once_with("other.als")
    assert result == []

def test_service_delegation_get_project_info(server):
    """
    Test delegation of get_project_info to QueryService.
    """
    server.query_service.get_project_info = MagicMock(return_value={})
    result = server.get_project_info()
    server.query_service.get_project_info.assert_called_once()
    assert result == {}

@pytest.mark.asyncio
async def test_process_live_event_routing(server):
    """
    Test process_live_event routes to correct handler.
    """
    server.current_ast = ProjectNode()
    
    # Mock specific handler method
    server.track_handler.handle_track_renamed = AsyncMock(return_value={"type": "renamed"})
    
    # Rebuild registry to include the mock (since registry is built in __init__)
    server._event_handlers = server._build_event_handler_registry()
    
    result = await server.process_live_event("/live/track/renamed", [0, "Name"], 1, 0.0)
    
    server.track_handler.handle_track_renamed.assert_called_once()
    assert result["type"] == "renamed"

@pytest.mark.asyncio
async def test_process_live_event_prefix_routing(server):
    """
    Test process_live_event routes prefix-based events (transport).
    """
    server.current_ast = ProjectNode()
    server.transport_handler.handle_transport_event = AsyncMock(return_value={"type": "transport"})
    
    result = await server.process_live_event("/live/transport/play", [True], 1, 0.0)
    
    server.transport_handler.handle_transport_event.assert_called_once()
    assert result["type"] == "transport"

@pytest.mark.asyncio
async def test_process_live_event_unknown(server):
    """
    Test process_live_event with unknown event type.
    """
    server.current_ast = ProjectNode()
    result = await server.process_live_event("/live/unknown", [], 1, 0.0)
    assert result is None

@pytest.mark.asyncio
async def test_process_live_event_no_ast(server):
    """
    Test process_live_event ignores events when no AST is loaded.
    """
    server.current_ast = None
    result = await server.process_live_event("/live/track/renamed", [], 1, 0.0)
    assert result is None

@pytest.mark.asyncio
async def test_process_live_event_exception_handling(server):
    """
    Test process_live_event handles exceptions during routing.
    """
    server.current_ast = ProjectNode()
    # Mock handler to raise exception
    server._event_handlers["/live/track/renamed"] = MagicMock(side_effect=Exception("Fail"))
    
    result = await server.process_live_event("/live/track/renamed", [], 1, 0.0)
    
    assert result is None
    server.websocket_server.broadcast_error.assert_called_once()
    args = server.websocket_server.broadcast_error.call_args[0]
    assert args[0] == "Event processing error"
    assert "Fail" in args[1]
