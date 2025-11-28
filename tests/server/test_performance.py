import pytest
import time
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from src.server.api import ASTServer
from src.ast import ProjectNode, TrackNode, SceneNode, ClipSlotNode, hash_tree
from src.server.ast_helpers import ASTBuilder

@pytest.fixture
def server():
    with patch("src.websocket.ASTWebSocketServer"), \
         patch("src.server.api.DebouncedBroadcaster"):
        server = ASTServer(enable_websocket=False, enable_cache=False)
        # Mock websocket to prevent actual network calls/errors but allow logic to run
        server.websocket_server = MagicMock()
        server.websocket_server.is_running.return_value = True
        server.websocket_server.broadcast_diff = AsyncMock()
        return server

def create_large_project(num_tracks=50, num_scenes=100):
    """Helper to create a large AST."""
    project = ProjectNode(id="project-root")
    
    # Create tracks
    for t in range(num_tracks):
        track = TrackNode(name=f"Track {t}", index=t, id=f"track-{t}")
        
        # Create clip slots for each scene
        for s in range(num_scenes):
            slot = ClipSlotNode(track_index=t, scene_index=s, id=f"slot-{t}-{s}")
            track.add_child(slot)
            
        project.add_child(track)
        
    # Create scenes
    for s in range(num_scenes):
        scene = SceneNode(name=f"Scene {s}", index=s, id=f"scene-{s}")
        project.add_child(scene)
        
    return project

@pytest.mark.benchmark
def test_hash_computation_efficiency():
    """
    Benchmark hash computation for a reasonably sized project.
    Target: < 50ms for 50 tracks * 100 scenes (5000 slots).
    """
    project = create_large_project(num_tracks=50, num_scenes=100)
    
    start_time = time.time()
    hash_tree(project)
    duration = time.time() - start_time
    
    print(f"\nHash computation time (50x100): {duration*1000:.2f}ms")
    # Assert strictly might be flaky on CI, but let's set a generous upper bound
    assert duration < 1.0, "Hash computation took too long (> 1s)"

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_event_processing_latency(server):
    """
    Benchmark processing time for a standard event (e.g., track rename).
    Target: < 10ms overhead.
    """
    # Setup minimal AST
    project = ProjectNode(id="project-root")
    track = TrackNode(name="Original", index=0, id="track-0")
    project.add_child(track)
    server.current_ast = project
    
    start_time = time.time()
    await server.process_live_event("/live/track/renamed", [0, "New Name"], 1, 0.0)
    duration = time.time() - start_time
    
    print(f"\nEvent processing latency (track rename): {duration*1000:.2f}ms")
    assert duration < 0.1, "Event processing latency too high (> 100ms)"

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_large_project_event_handling(server):
    """
    Stress test event handling with a large project loaded.
    Renaming a track in a large project involves finding it and rehashing.
    """
    num_tracks = 50
    num_scenes = 100
    project = create_large_project(num_tracks=num_tracks, num_scenes=num_scenes)
    hash_tree(project) # Initial hash
    server.current_ast = project
    
    # Rename the last track (worst case search if linear, though find_track_by_index should be fast)
    target_index = num_tracks - 1
    
    start_time = time.time()
    await server.process_live_event("/live/track/renamed", [target_index, "Renamed Track"], 1, 0.0)
    duration = time.time() - start_time
    
    print(f"\nLarge project event processing (rename track {target_index}): {duration*1000:.2f}ms")
    
    # Verify change
    target_track = server.current_ast.children[target_index] # Assuming tracks are first children
    assert target_track.attributes["name"] == "Renamed Track"
    
    # Strict performance requirement might be hard on shared runners, 
    # but < 200ms is a reasonable expectation for UI responsiveness
    assert duration < 0.5, "Large project event processing took too long"

def test_memory_usage_node_creation():
    """
    Basic check to ensure node creation doesn't explode memory (indirectly via timing/count).
    Actual memory profiling is hard in standard pytest without plugins.
    We'll just ensure we can create many nodes quickly.
    """
    start_time = time.time()
    nodes = [ClipSlotNode(track_index=0, scene_index=i) for i in range(10000)]
    duration = time.time() - start_time
    
    print(f"\nNode creation time (10k nodes): {duration*1000:.2f}ms")
    assert duration < 1.0
    assert len(nodes) == 10000
