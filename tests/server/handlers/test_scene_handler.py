import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.server.handlers.scene_handler import SceneEventHandler
from src.ast import SceneNode, ProjectNode, NodeType, TrackNode, ClipSlotNode

class MockServer:
    def __init__(self):
        self.current_ast = ProjectNode()
        self.websocket_server = MagicMock()
        self.websocket_server.is_running.return_value = True
        self.websocket_server.broadcast_diff = AsyncMock()
        self.websocket_server.broadcast_error = AsyncMock()
        self.cache = MagicMock()

@pytest.fixture
def server():
    return MockServer()

@pytest.fixture
def handler(server):
    return SceneEventHandler(server)

@pytest.mark.asyncio
async def test_handle_scene_renamed_valid(handler, server):
    """
    Test handle_scene_renamed with valid arguments and existing scene.
    """
    scene_node = SceneNode(name="Old Scene", index=0)
    scene_node.id = "scene-0"
    server.current_ast.children = [scene_node]
    scene_node.parent = server.current_ast

    with patch("src.server.handlers.scene_handler.ASTNavigator.find_scene_by_index", return_value=scene_node):
        args = [0, "New Scene"]
        result = await handler.handle_scene_renamed(args, seq_num=1)

    assert result is not None
    assert result["type"] == "scene_renamed"
    assert result["name"] == "New Scene"
    
    # Verify AST update
    assert scene_node.attributes["name"] == "New Scene"
    
    # Verify broadcast
    server.websocket_server.broadcast_diff.assert_called_once()
    diff_result = server.websocket_server.broadcast_diff.call_args[0][0]
    assert len(diff_result["changes"]) == 1
    assert diff_result["changes"][0]["type"] == "modified"
    assert diff_result["changes"][0]["path"] == "scenes[0]"
    assert diff_result["changes"][0]["new_value"] == {"name": "New Scene"}

@pytest.mark.asyncio
async def test_handle_scene_renamed_not_found(handler):
    """
    Test handle_scene_renamed when scene is not found.
    """
    with patch("src.server.handlers.scene_handler.ASTNavigator.find_scene_by_index", return_value=None):
        args = [99, "New Scene"]
        result = await handler.handle_scene_renamed(args, seq_num=1)

    assert result is None

@pytest.mark.asyncio
async def test_handle_scene_added_simple(handler, server):
    """
    Test handle_scene_added adding to the end.
    """
    # Setup existing scene
    existing_scene = SceneNode(name="Scene 1", index=0)
    existing_scene.id = "scene-0"
    server.current_ast.children = [existing_scene]
    existing_scene.parent = server.current_ast

    # Mock ASTNavigator.get_scenes to return existing scenes
    with patch("src.server.handlers.scene_handler.ASTNavigator.get_scenes", return_value=[existing_scene]):
        # Mock SceneIndexManager methods to return empty changes (no shifting needed for append)
        with patch("src.server.handlers.scene_handler.SceneIndexManager.shift_scene_indices", return_value=[]) as mock_shift_scenes, \
             patch("src.server.handlers.scene_handler.SceneIndexManager.shift_clip_slot_indices", return_value=[]) as mock_shift_slots:
            
            args = [1, "Scene 2"]
            result = await handler.handle_scene_added(args, seq_num=2)

    assert result is not None
    assert result["type"] == "scene_added"
    assert result["scene_idx"] == 1
    assert result["name"] == "Scene 2"

    # Verify AST update - should be added to children
    assert len(server.current_ast.children) == 2
    new_scene = server.current_ast.children[1]
    assert new_scene.node_type == NodeType.SCENE
    assert new_scene.attributes["name"] == "Scene 2"
    assert new_scene.attributes["index"] == 1

    # Verify broadcast
    server.websocket_server.broadcast_diff.assert_called_once()
    diff_result = server.websocket_server.broadcast_diff.call_args[0][0]
    # Should have 1 added change
    assert len(diff_result["changes"]) == 1
    assert diff_result["changes"][0]["type"] == "added"
    assert diff_result["changes"][0]["new_value"]["name"] == "Scene 2"

@pytest.mark.asyncio
async def test_handle_scene_removed_valid(handler, server):
    """
    Test handle_scene_removed.
    """
    scene_node = SceneNode(name="Scene To Remove", index=0)
    scene_node.id = "scene-0"
    server.current_ast.children = [scene_node]
    scene_node.parent = server.current_ast

    with patch("src.server.handlers.scene_handler.ASTNavigator.find_scene_by_index", return_value=scene_node), \
         patch("src.server.handlers.scene_handler.ASTNavigator.get_tracks", return_value=[]), \
         patch("src.server.handlers.scene_handler.SceneIndexManager.shift_scene_indices", return_value=[]), \
         patch("src.server.handlers.scene_handler.SceneIndexManager.shift_clip_slot_indices", return_value=[]):
        
        args = [0]
        result = await handler.handle_scene_removed(args, seq_num=3)

    assert result is not None
    assert result["type"] == "scene_removed"
    assert result["scene_idx"] == 0

    # Verify AST update - child removed
    assert len(server.current_ast.children) == 0

    # Verify broadcast
    server.websocket_server.broadcast_diff.assert_called_once()
    diff_result = server.websocket_server.broadcast_diff.call_args[0][0]
    assert len(diff_result["changes"]) == 1
    assert diff_result["changes"][0]["type"] == "removed"
    assert diff_result["changes"][0]["node_id"] == "scene-0"

@pytest.mark.asyncio
async def test_handle_scene_reordered_ignored(handler):
    """
    Test handle_scene_reordered returns ignored status.
    """
    args = [1, "Scene Name"]
    result = await handler.handle_scene_reordered(args, seq_num=4)

    assert result is not None
    assert result["type"] == "scene_reordered"
    assert result["ignored"] is True
