import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.server.handlers.clip_slot_handler import ClipSlotEventHandler
from src.ast import TrackNode, ClipSlotNode, ProjectNode

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
    return ClipSlotEventHandler(server)

@pytest.mark.asyncio
async def test_handle_clip_slot_created_new(handler, server):
    """
    Test handle_clip_slot_created when creating a new slot.
    """
    # Setup AST
    track_node = TrackNode(name="Audio 1", index=0)
    track_node.id = "track-0"
    server.current_ast.children = [track_node]
    track_node.parent = server.current_ast

    # Mock dependencies
    with patch("src.server.handlers.clip_slot_handler.BaseEventHandler._find_track", return_value=track_node), \
         patch("src.server.handlers.clip_slot_handler.ClipSlotManager.find_existing_slot", return_value=None), \
         patch("src.server.handlers.clip_slot_handler.ClipSlotManager.create_clip_slot_node") as mock_create_node, \
         patch("src.server.handlers.clip_slot_handler.ClipSlotManager.insert_clip_slot") as mock_insert:
        
        # Setup mock new slot
        new_slot = ClipSlotNode(track_index=0, scene_index=0)
        new_slot.id = "slot-0"
        mock_create_node.return_value = new_slot

        args = [0, 0, False, True, 0] # track_idx, scene_idx, has_clip, has_stop, status
        result = await handler.handle_clip_slot_created(args, seq_num=1)

    assert result is not None
    assert result["type"] == "clip_slot_created"
    
    # Verify mocks called
    mock_create_node.assert_called_once()
    mock_insert.assert_called_once_with(track_node, new_slot, 0)
    
    # Verify broadcast
    server.websocket_server.broadcast_diff.assert_called_once()
    diff_result = server.websocket_server.broadcast_diff.call_args[0][0]
    assert len(diff_result["changes"]) == 1
    assert diff_result["changes"][0]["type"] == "added"
    assert diff_result["changes"][0]["node_id"] == "slot-0"

@pytest.mark.asyncio
async def test_handle_clip_slot_created_existing(handler, server):
    """
    Test handle_clip_slot_created when slot already exists (update).
    """
    # Setup AST
    track_node = TrackNode(name="Audio 1", index=0)
    track_node.id = "track-0"
    existing_slot = ClipSlotNode(track_index=0, scene_index=0)
    existing_slot.id = "slot-0"
    track_node.add_child(existing_slot)
    server.current_ast.children = [track_node]
    track_node.parent = server.current_ast

    # Mock dependencies
    with patch("src.server.handlers.clip_slot_handler.BaseEventHandler._find_track", return_value=track_node), \
         patch("src.server.handlers.clip_slot_handler.ClipSlotManager.find_existing_slot", return_value=existing_slot), \
         patch("src.server.handlers.clip_slot_handler.ClipSlotManager.update_clip_slot_attributes") as mock_update:
        
        args = [0, 0, True, True, 1] # has_clip=True, status=1 (playing)
        result = await handler.handle_clip_slot_created(args, seq_num=2)

    assert result is not None
    
    # Verify update called
    mock_update.assert_called_once_with(existing_slot, True, True, 1)
    
    # Verify broadcast (should be modified diff)
    server.websocket_server.broadcast_diff.assert_called_once()
    diff_result = server.websocket_server.broadcast_diff.call_args[0][0]
    assert len(diff_result["changes"]) == 1
    assert diff_result["changes"][0]["type"] == "modified"
    assert diff_result["changes"][0]["node_id"] == "slot-0"
