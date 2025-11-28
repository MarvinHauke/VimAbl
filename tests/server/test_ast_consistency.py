import pytest
from src.server.handlers.track_handler import TrackEventHandler
from src.server.api import ASTServer
from src.ast import ProjectNode, TrackNode, hash_tree

class MockServer:
    def __init__(self):
        self.current_ast = None
        self.websocket_server = None

@pytest.fixture
def server():
    return MockServer()

@pytest.fixture
def track_handler(server):
    return TrackEventHandler(server)

@pytest.mark.asyncio
async def test_hash_propagation_on_track_rename(track_handler, server):
    """
    Test that renaming a track updates its hash and the project root hash.
    """
    # Setup AST
    project = ProjectNode(id="project-root")
    track = TrackNode(name="Old Name", index=0)
    track.id = "track-0"
    project.add_child(track)
    
    # Initial hashes
    hash_tree(project)
    initial_project_hash = project.hash
    initial_track_hash = track.hash
    
    server.current_ast = project
    
    # Perform rename via handler (which calls _recompute_parent_hashes)
    await track_handler.handle_track_renamed([0, "New Name"], seq_num=1)
    
    # Check hashes changed
    assert track.attributes["name"] == "New Name"
    assert track.hash != initial_track_hash
    assert project.hash != initial_project_hash
    
    # Verify new hash is consistent
    expected_track_hash = track.hash
    hash_tree(project) # Recompute entire tree to verify
    assert track.hash == expected_track_hash
    assert project.hash is not None

@pytest.mark.asyncio
async def test_hash_propagation_on_track_state_change(track_handler, server):
    """
    Test that changing track state updates hashes.
    """
    # Setup AST
    project = ProjectNode(id="project-root")
    track = TrackNode(name="Audio 1", index=0)
    track.attributes["is_muted"] = False
    track.id = "track-0"
    project.add_child(track)
    
    hash_tree(project)
    initial_project_hash = project.hash
    
    server.current_ast = project
    
    # Mute track
    await track_handler.handle_track_state([0, True], seq_num=1, attribute="is_muted")
    
    assert track.attributes["is_muted"] is True
    assert project.hash != initial_project_hash
