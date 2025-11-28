import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.server.handlers.device_handler import DeviceEventHandler
from src.ast import TrackNode, DeviceNode, ProjectNode, NodeType

class MockServer:
    def __init__(self):
        self.current_ast = ProjectNode()
        self.websocket_server = MagicMock()
        self.websocket_server.is_running.return_value = True
        self.websocket_server.broadcast_diff = AsyncMock()
        self.websocket_server.broadcast_error = AsyncMock()
        self.debouncer = MagicMock()
        self.debouncer.debounce = AsyncMock()

@pytest.fixture
def server():
    return MockServer()

@pytest.fixture
def handler(server):
    return DeviceEventHandler(server)

@pytest.mark.asyncio
async def test_handle_device_added_valid(handler, server):
    """
    Test handle_device_added with valid arguments.
    """
    # Setup AST
    track_node = TrackNode(name="Audio 1", index=0)
    track_node.id = "track-0"
    server.current_ast.children = [track_node]
    track_node.parent = server.current_ast

    with patch("src.server.handlers.device_handler.BaseEventHandler._find_track", return_value=track_node):
        args = [0, 0, "Reverb"]
        result = await handler.handle_device_added(args, seq_num=1)

    assert result is not None
    assert result["type"] == "device_added"
    assert result["name"] == "Reverb"
    
    # Verify AST update
    assert len(track_node.children) == 1
    assert track_node.children[0].node_type == NodeType.DEVICE
    assert track_node.children[0].attributes["name"] == "Reverb"
    
    # Verify broadcast
    server.websocket_server.broadcast_diff.assert_called_once()
    diff_result = server.websocket_server.broadcast_diff.call_args[0][0]
    assert len(diff_result["changes"]) == 1
    assert diff_result["changes"][0]["type"] == "added"
    assert diff_result["changes"][0]["new_value"]["name"] == "Reverb"

@pytest.mark.asyncio
async def test_handle_device_deleted_valid(handler, server):
    """
    Test handle_device_deleted with valid arguments.
    """
    # Setup AST
    track_node = TrackNode(name="Audio 1", index=0)
    track_node.id = "track-0"
    device_node = DeviceNode(name="Reverb", device_type="audio_effect")
    device_node.id = "device-0"
    track_node.add_child(device_node)
    server.current_ast.children = [track_node]
    track_node.parent = server.current_ast

    with patch("src.server.handlers.device_handler.BaseEventHandler._find_track", return_value=track_node):
        args = [0, 0]
        result = await handler.handle_device_deleted(args, seq_num=2)

    assert result is not None
    assert result["type"] == "device_deleted"
    
    # Verify AST update
    assert len(track_node.children) == 0
    
    # Verify broadcast
    server.websocket_server.broadcast_diff.assert_called_once()
    diff_result = server.websocket_server.broadcast_diff.call_args[0][0]
    assert len(diff_result["changes"]) == 1
    assert diff_result["changes"][0]["type"] == "removed"
    assert diff_result["changes"][0]["node_id"] == "device-0"

@pytest.mark.asyncio
async def test_handle_device_param_update(handler, server):
    """
    Test handle_device_param triggers debouncer.
    """
    # Setup AST
    track_node = TrackNode(name="Audio 1", index=0)
    device_node = DeviceNode(name="Reverb", device_type="audio_effect")
    device_node.attributes["parameters"] = [{'name': 'Decay', 'value': 0.5}]
    device_node.id = "device-0"
    track_node.add_child(device_node)
    server.current_ast.children = [track_node]
    track_node.parent = server.current_ast

    with patch("src.server.handlers.device_handler.BaseEventHandler._find_track", return_value=track_node):
        args = [0, 0, 0, 0.8] # Track 0, Device 0, Param 0, Value 0.8
        result = await handler.handle_device_param(args, seq_num=3)

    assert result is not None
    assert result["type"] == "param_event"
    
    # Verify AST update immediate (debouncing is for broadcast, but implementation updates AST first?)
    # Let's check implementation.
    # Yes, it updates self.ast params first, THEN debounces broadcast.
    assert device_node.attributes["parameters"][0]["value"] == 0.8
    
    # Verify debouncer called
    server.debouncer.debounce.assert_called_once()
    call_args = server.debouncer.debounce.call_args
    assert call_args[0][0] == "device_parameter_changed"
    assert call_args[0][1]["parameter_value"] == 0.8

@pytest.mark.asyncio
async def test_broadcast_device_param_change(handler, server):
    """
    Test broadcast_device_param_change broadcasts correctly.
    """
    event_args = {
        'track_index': 0,
        'device_index': 0,
        'parameter_index': 0,
        'parameter_value': 0.8,
        'device_node_id': 'device-0',
        'seq_num': 4
    }
    
    await handler.broadcast_device_param_change("device_parameter_changed", event_args)
    
    server.websocket_server.broadcast_diff.assert_called_once()
    diff_result = server.websocket_server.broadcast_diff.call_args[0][0]
    assert len(diff_result["changes"]) == 1
    assert diff_result["changes"][0]["type"] == "state_changed"
    assert diff_result["changes"][0]["value"] == 0.8
    assert diff_result["changes"][0]["node_id"] == "device-0"
