import pytest
import asyncio
import uuid
from src.server.api import ASTServer
from src.ast import ProjectNode, TrackNode, SceneNode, ClipSlotNode, NodeType

@pytest.mark.asyncio
async def test_handle_scene_added_shifts_indices_uuid():
    # Setup AST
    server = ASTServer()
    server.current_ast = ProjectNode(id="project")
    
    # Add tracks
    track = TrackNode(name="Track 1", index=0, id="track_0")
    server.current_ast.add_child(track)
    
    # Add Scenes 0, 1 (representing initial state with UUIDs)
    id0 = f"scene_{uuid.uuid4().hex[:8]}"
    id1 = f"scene_{uuid.uuid4().hex[:8]}"
    scene0 = SceneNode(name="Scene 0", index=0, id=id0)
    scene1 = SceneNode(name="Scene 1", index=1, id=id1)
    server.current_ast.add_child(scene0)
    server.current_ast.add_child(scene1)
    
    # Add Clip Slots for Scenes 0, 1 with UUIDs
    slot_id0 = f"clip_slot_{uuid.uuid4().hex[:8]}"
    slot_id1 = f"clip_slot_{uuid.uuid4().hex[:8]}"
    slot0 = ClipSlotNode(track_index=0, scene_index=0, id=slot_id0)
    slot1 = ClipSlotNode(track_index=0, scene_index=1, id=slot_id1)
    track.add_child(slot0)
    track.add_child(slot1)
    
    # Verify initial state
    assert len(server.current_ast.children) == 3 # 1 track + 2 scenes
    assert len(track.children) == 2
    
    # Insert new Scene at index 1 (should shift old Scene 1 to index 2)
    await server._handle_scene_added([1, "New Scene"], seq_num=1)
    
    # Verify Scenes
    scenes = [c for c in server.current_ast.children if c.node_type == NodeType.SCENE]
    assert len(scenes) == 3
    
    # Verify indices and IDs
    s0 = next(s for s in scenes if s.id == id0)
    s_new = next(s for s in scenes if s.attributes['name'] == "New Scene")
    s1_old = next(s for s in scenes if s.id == id1)
    
    assert s0.attributes['index'] == 0
    assert s_new.attributes['index'] == 1
    assert s1_old.attributes['index'] == 2 # Shifted!
    assert s_new.id.startswith("scene_") # Check new ID format
    assert len(s_new.id) > 10 # Check it has UUID part
    
    # Verify Clip Slots
    slots = [c for c in track.children if c.node_type == NodeType.CLIP_SLOT]
    
    slot0 = next(s for s in slots if s.id == slot_id0)
    slot1_old = next(s for s in slots if s.id == slot_id1)
    
    assert slot0.attributes['scene_index'] == 0
    assert slot1_old.attributes['scene_index'] == 2 # Shifted!

if __name__ == "__main__":
    asyncio.run(test_handle_scene_added_shifts_indices_uuid())
