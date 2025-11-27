import pytest
import asyncio
import uuid
from src.server.api import ASTServer
from src.ast import ProjectNode, TrackNode, SceneNode, ClipSlotNode, NodeType

@pytest.mark.asyncio
async def test_full_insertion_flow():
    # Setup AST with 1 track and 2 scenes (0, 1)
    server = ASTServer()
    server.current_ast = ProjectNode(id="project")
    
    track = TrackNode(name="Track 1", index=0, id="track_0")
    server.current_ast.add_child(track)
    
    # Scene 0
    s0 = SceneNode(name="Scene 0", index=0, id=f"scene_{uuid.uuid4().hex[:8]}")
    server.current_ast.add_child(s0)
    cs0 = ClipSlotNode(track_index=0, scene_index=0, id=f"slot_{uuid.uuid4().hex[:8]}")
    track.add_child(cs0)
    
    # Scene 1
    s1 = SceneNode(name="Scene 1", index=1, id=f"scene_{uuid.uuid4().hex[:8]}")
    server.current_ast.add_child(s1)
    cs1 = ClipSlotNode(track_index=0, scene_index=1, id=f"slot_{uuid.uuid4().hex[:8]}")
    track.add_child(cs1)
    
    # Initial verification
    assert len(server.current_ast.children) == 3 # 1 track + 2 scenes
    assert len(track.children) == 2
    assert cs0.attributes['scene_index'] == 0
    assert cs1.attributes['scene_index'] == 1
    
    # ACTION: Insert new scene at index 1
    # This simulates what happens when ObserverManager detects a scene addition
    
    # 1. Server receives /live/scene/added 1
    await server._handle_scene_added([1, "Inserted Scene"], seq_num=1)
    
    # Verify state after scene addition (but before slot creation)
    # Existing Scene 1 should have shifted to 2
    # Existing Slot 1 should have shifted to 2
    # New Scene should be at 1
    assert len(server.current_ast.children) == 4
    
    s1_new = next(s for s in server.current_ast.children if s.node_type == NodeType.SCENE and s.attributes['index'] == 1)
    s2_old = next(s for s in server.current_ast.children if s.node_type == NodeType.SCENE and s.attributes['index'] == 2)
    
    assert s1_new.attributes['name'] == "Inserted Scene"
    assert s2_old.id == s1.id # The old scene object shifted
    
    cs1_old = next(s for s in track.children if s.node_type == NodeType.CLIP_SLOT and s.attributes['scene_index'] == 2)
    assert cs1_old.id == cs1.id # The old slot object shifted
    
    # 2. Server receives /live/clip_slot/created 1 (triggered by ObserverManager)
    await server._handle_clip_slot_created([0, 1, False, True, 0], seq_num=2)
    
    # Verify final state
    # Should have slots at 0, 1, 2
    slots = [c for c in track.children if c.node_type == NodeType.CLIP_SLOT]
    assert len(slots) == 3
    
    slot_indices = sorted([s.attributes['scene_index'] for s in slots])
    assert slot_indices == [0, 1, 2]
    
    # Verify no duplicates or weirdness
    slot_at_1 = next(s for s in slots if s.attributes['scene_index'] == 1)
    assert slot_at_1.id != cs1.id # Should be a new object
    assert slot_at_1.attributes['has_clip'] is False

if __name__ == "__main__":
    asyncio.run(test_full_insertion_flow())
