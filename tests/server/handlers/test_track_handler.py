import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.server.handlers.track_handler import TrackEventHandler
from src.ast import TrackNode, ProjectNode

class MockServer:
    def __init__(self):
        self.current_ast = ProjectNode()
        self.websocket_server = MagicMock()
        self.websocket_server.is_running.return_value = True
        self.websocket_server.broadcast_diff = AsyncMock()
        self.websocket_server.broadcast_error = AsyncMock()

@pytest.fixture
def server():
    return MockServer()

@pytest.fixture
def handler(server):
    return TrackEventHandler(server)

@pytest.mark.asyncio
async def test_handle_track_renamed_valid(handler, server):
    """
    Test handle_track_renamed with valid arguments and existing track.
    """
    # Setup AST
    track_node = TrackNode(name="Old Name", index=0)
    track_node.id = "track-0"
    server.current_ast.children = [track_node]
    track_node.parent = server.current_ast # Needed for _recompute_parent_hashes

    # Mock finding track
    with patch("src.server.ast_helpers.ASTNavigator.find_track_by_index", return_value=track_node):
        args = [0, "New Name"]
        result = await handler.handle_track_renamed(args, seq_num=1)

    assert result is not None
    assert result["type"] == "track_renamed"
    assert result["name"] == "New Name"
    
    # Verify AST update
    assert track_node.attributes["name"] == "New Name"
    
    # Verify broadcast
    server.websocket_server.broadcast_diff.assert_called_once()
    call_args = server.websocket_server.broadcast_diff.call_args[0][0]
    assert len(call_args["changes"]) == 1
    assert call_args["changes"][0]["type"] == "modified"
    assert call_args["changes"][0]["path"] == "tracks[0]"
    assert call_args["changes"][0]["new_value"] == {"name": "New Name"}

@pytest.mark.asyncio
async def test_handle_track_renamed_track_not_found(handler):
    """
    Test handle_track_renamed when track is not found.
    """
    with patch("src.server.ast_helpers.ASTNavigator.find_track_by_index", return_value=None):
        args = [99, "New Name"]
        result = await handler.handle_track_renamed(args, seq_num=1)

    assert result is None

@pytest.mark.asyncio
async def test_handle_track_state_mute(handler, server):
    """
    Test handle_track_state for mute property.
    """
    # Setup AST
    track_node = TrackNode(name="Audio 1", index=0)
    track_node.attributes['is_muted'] = False
    track_node.id = "track-0"
    server.current_ast.children = [track_node]
    track_node.parent = server.current_ast

    # Mock finding track
    with patch("src.server.ast_helpers.ASTNavigator.find_track_by_index", return_value=track_node):
        args = [0, True]
        result = await handler.handle_track_state(args, seq_num=2, attribute="is_muted")

    assert result is not None
    assert result["type"] == "track_state"
    assert result["attribute"] == "is_muted"
    assert result["value"] is True
    
    # Verify AST update
    assert track_node.attributes["is_muted"] is True
    
    # Verify broadcast
    server.websocket_server.broadcast_diff.assert_called_once()
    call_args = server.websocket_server.broadcast_diff.call_args[0][0]
    assert len(call_args["changes"]) == 1
    assert call_args["changes"][0]["type"] == "state_changed"
    assert call_args["changes"][0]["attribute"] == "is_muted"
    assert call_args["changes"][0]["new_value"] is True

@pytest.mark.asyncio
async def test_handle_track_state_volume(handler, server):
    """
    Test handle_track_state for volume property.
    """
    # Setup AST
    track_node = TrackNode(name="Audio 1", index=0)
    track_node.attributes['volume'] = 0.85
    track_node.id = "track-0"
    server.current_ast.children = [track_node]
    track_node.parent = server.current_ast

    with patch("src.server.ast_helpers.ASTNavigator.find_track_by_index", return_value=track_node):
        args = [0, 0.5]
        result = await handler.handle_track_state(args, seq_num=3, attribute="volume")

    assert result is not None
    assert result["value"] == 0.5
    assert track_node.attributes["volume"] == 0.5

@pytest.mark.asyncio
async def test_handle_track_state_track_not_found(handler):
    """
    Test handle_track_state when track is not found.
    """
    with patch("src.server.ast_helpers.ASTNavigator.find_track_by_index", return_value=None):
        args = [0, True]
        result = await handler.handle_track_state(args, seq_num=1, attribute="is_muted")

    assert result is None

@pytest.mark.asyncio
async def test_handle_track_renamed_invalid_args(handler):
    """
    Test handle_track_renamed with insufficient arguments.
    """
    args = [0] # Missing name
    result = await handler.handle_track_renamed(args, seq_num=1)
    assert result is None

@pytest.mark.asyncio
async def test_handle_track_state_invalid_args(handler):
    """
    Test handle_track_state with insufficient arguments.
    """
    args = [0] # Missing value
    result = await handler.handle_track_state(args, seq_num=1, attribute="is_muted")
    assert result is None
