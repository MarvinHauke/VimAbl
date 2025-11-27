import pytest
import asyncio
from src.server.api import ASTServer
from src.ast import ProjectNode, TrackNode, SceneNode, ClipSlotNode, NodeType

@pytest.mark.asyncio
async def test_handle_scene_removed_shifts_indices():
    # Setup AST
    server = ASTServer()
    server.current_ast = ProjectNode(id="project")
    
    # Add tracks
    track = TrackNode(name="Track 1", index=0, id="track_0")
    server.current_ast.add_child(track)
    
    # Add Scenes 0, 1, 2
    scene0 = SceneNode(name="Scene 0", index=0, id="scene_0")
    scene1 = SceneNode(name="Scene 1", index=1, id="scene_1")
    scene2 = SceneNode(name="Scene 2", index=2, id="scene_2")
    server.current_ast.add_child(scene0)
    server.current_ast.add_child(scene1)
    server.current_ast.add_child(scene2)
    
    # Add Clip Slots for Scenes 0, 1, 2
    slot0 = ClipSlotNode(track_index=0, scene_index=0, id="slot_0_0")
    slot1 = ClipSlotNode(track_index=0, scene_index=1, id="slot_0_1")
    slot2 = ClipSlotNode(track_index=0, scene_index=2, id="slot_0_2")
    track.add_child(slot0)
    track.add_child(slot1)
    track.add_child(slot2)
    
    # Verify initial state
    assert len(server.current_ast.children) == 4 # 1 track + 3 scenes
    assert len(track.children) == 3
    
    # Remove Scene 1
    # This should remove scene1 and slot1
    # And shift scene2 index to 1, slot2 scene_index to 1
    await server._handle_scene_removed([1], seq_num=1)
    
    # Verify Scene removal
    scenes = [c for c in server.current_ast.children if c.node_type == NodeType.SCENE]
    assert len(scenes) == 2
    assert any(s.id == "scene_0" for s in scenes)
    assert not any(s.id == "scene_1" for s in scenes)
    assert any(s.id == "scene_2" for s in scenes)
    
    # Verify Scene shifting
    s2 = next(s for s in scenes if s.id == "scene_2")
    assert s2.attributes['index'] == 1
    
    # Verify Clip Slot removal
    slots = [c for c in track.children if c.node_type == NodeType.CLIP_SLOT]
    assert len(slots) == 2
    assert any(s.id == "slot_0_0" for s in slots)
    assert not any(s.id == "slot_0_1" for s in slots)
    assert any(s.id == "slot_0_2" for s in slots)
    
    # Verify Clip Slot shifting
    slot2 = next(s for s in slots if s.id == "slot_0_2")
    assert slot2.attributes['scene_index'] == 1

if __name__ == "__main__":
    asyncio.run(test_handle_scene_removed_shifts_indices())
