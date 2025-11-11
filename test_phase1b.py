#!/usr/bin/env python3
"""
Test script for Phase 1b: Scenes & Mixer

This script verifies that scene and mixer extraction is working correctly.
"""

from pathlib import Path
from src.server import ASTServer
from src.ast import NodeType

def test_phase1b():
    """Test Phase 1b implementation with example project."""

    print("=" * 60)
    print("PHASE 1B TEST: Scenes & Mixer")
    print("=" * 60)
    print()

    # Load the example project
    server = ASTServer()
    project_path = Path("Example_Project/example.als")

    if not project_path.exists():
        print(f"❌ ERROR: {project_path} not found!")
        return False

    print(f"📂 Loading project: {project_path}")
    server.load_project(project_path)
    print("✅ Project loaded successfully")
    print()

    # Test 1: Get project info
    print("TEST 1: Project Info")
    print("-" * 60)
    info = server.get_project_info()
    print(f"  Tracks:     {info['num_tracks']}")
    print(f"  Devices:    {info['num_devices']}")
    print(f"  Clips:      {info['num_clips']}")
    print(f"  Scenes:     {info['num_scenes']} ⭐ NEW")
    print(f"  File Refs:  {info['num_file_refs']}")

    if info['num_scenes'] == 0:
        print("❌ FAIL: No scenes found!")
        return False
    print("✅ PASS: Scenes detected")
    print()

    # Test 2: Scene extraction details
    print("TEST 2: Scene Extraction")
    print("-" * 60)
    scenes = server.search_visitor.find_by_type(server.current_ast, NodeType.SCENE)

    if len(scenes) == 0:
        print("❌ FAIL: No scene nodes found!")
        return False

    print(f"  Total scenes: {len(scenes)}")

    # Check first few scenes
    for i, scene in enumerate(scenes[:3]):
        print(f"\n  Scene {i}:")
        print(f"    Name:                 '{scene.attributes.get('name')}'")
        print(f"    Index:                {scene.attributes.get('index')}")
        print(f"    Color:                {scene.attributes.get('color')}")
        print(f"    Tempo:                {scene.attributes.get('tempo')}")
        print(f"    Tempo Enabled:        {scene.attributes.get('is_tempo_enabled')}")
        print(f"    Time Signature ID:    {scene.attributes.get('time_signature_id')}")
        print(f"    Time Sig Enabled:     {scene.attributes.get('is_time_signature_enabled')}")

    # Verify scene attributes
    required_attrs = ['name', 'index', 'color', 'tempo', 'is_tempo_enabled',
                     'time_signature_id', 'is_time_signature_enabled', 'annotation']

    for attr in required_attrs:
        if attr not in scenes[0].attributes:
            print(f"❌ FAIL: Missing scene attribute: {attr}")
            return False

    print("\n✅ PASS: All scene attributes present")
    print()

    # Test 3: Mixer extraction details
    print("TEST 3: Mixer Extraction")
    print("-" * 60)
    tracks = server.search_visitor.find_by_type(server.current_ast, NodeType.TRACK)

    if len(tracks) == 0:
        print("❌ FAIL: No tracks found!")
        return False

    # Find tracks with mixer nodes
    tracks_with_mixer = []
    for track in tracks[:5]:  # Check first 5 tracks
        mixer_nodes = [c for c in track.children if c.node_type == NodeType.MIXER]
        if mixer_nodes:
            tracks_with_mixer.append((track, mixer_nodes[0]))

    if len(tracks_with_mixer) == 0:
        print("❌ FAIL: No mixer nodes found!")
        return False

    print(f"  Tracks with mixer: {len(tracks_with_mixer)}/{min(5, len(tracks))}")

    # Check first few mixers
    for i, (track, mixer) in enumerate(tracks_with_mixer[:3]):
        print(f"\n  Track {track.attributes.get('index')} - '{track.attributes.get('name')}':")
        print(f"    Volume:        {mixer.attributes.get('volume')}")
        print(f"    Pan:           {mixer.attributes.get('pan')}")
        print(f"    Muted:         {mixer.attributes.get('is_muted')}")
        print(f"    Soloed:        {mixer.attributes.get('is_soloed')}")
        print(f"    Crossfader:    {mixer.attributes.get('crossfader')}")
        sends = mixer.attributes.get('sends', [])
        print(f"    Sends:         {len(sends)}")
        for send_idx, send in enumerate(sends):
            print(f"      Send {send_idx}: level={send.get('level'):.3f}, active={send.get('is_active')}")

    # Verify mixer attributes
    required_mixer_attrs = ['volume', 'pan', 'is_muted', 'is_soloed', 'crossfader', 'sends']

    for attr in required_mixer_attrs:
        if attr not in tracks_with_mixer[0][1].attributes:
            print(f"❌ FAIL: Missing mixer attribute: {attr}")
            return False

    print("\n✅ PASS: All mixer attributes present")
    print()

    # Test 4: Mixer value ranges
    print("TEST 4: Mixer Value Validation")
    print("-" * 60)

    for track, mixer in tracks_with_mixer:
        volume = mixer.attributes.get('volume')
        pan = mixer.attributes.get('pan')

        # Volume should be positive (0.0 to 2.0+)
        if volume < 0:
            print(f"❌ FAIL: Invalid volume value: {volume}")
            return False

        # Pan should be between -1.0 and 1.0
        if not (-1.0 <= pan <= 1.0):
            print(f"❌ FAIL: Invalid pan value: {pan}")
            return False

        # Check send levels
        sends = mixer.attributes.get('sends', [])
        for send in sends:
            level = send.get('level')
            if level < 0 or level > 1.0:
                print(f"❌ FAIL: Invalid send level: {level}")
                return False

    print("  Volume ranges: ✅ Valid")
    print("  Pan ranges:    ✅ Valid")
    print("  Send levels:   ✅ Valid")
    print()

    # Test 5: AST Structure
    print("TEST 5: AST Structure Validation")
    print("-" * 60)

    # Scenes should be children of project
    project_node = server.current_ast
    scene_children = [c for c in project_node.children if c.node_type == NodeType.SCENE]
    print(f"  Scenes as project children:     {len(scene_children)}")

    # Mixer should be children of tracks
    total_mixer_nodes = 0
    for track in tracks:
        mixer_children = [c for c in track.children if c.node_type == NodeType.MIXER]
        total_mixer_nodes += len(mixer_children)

    print(f"  Mixer nodes as track children:  {total_mixer_nodes}")

    if len(scene_children) == 0:
        print("❌ FAIL: Scenes not properly attached to project!")
        return False

    if total_mixer_nodes == 0:
        print("❌ FAIL: Mixer nodes not properly attached to tracks!")
        return False

    print("✅ PASS: AST structure is correct")
    print()

    # Test 6: Hashing
    print("TEST 6: Hash Computation")
    print("-" * 60)

    # Check that scenes have hashes
    scenes_with_hash = [s for s in scenes if s.hash is not None]
    print(f"  Scenes with hash:  {len(scenes_with_hash)}/{len(scenes)}")

    # Check that mixers have hashes
    all_mixers = server.search_visitor.find_by_type(server.current_ast, NodeType.MIXER)
    mixers_with_hash = [m for m in all_mixers if m.hash is not None]
    print(f"  Mixers with hash:  {len(mixers_with_hash)}/{len(all_mixers)}")

    if len(scenes_with_hash) == 0:
        print("❌ FAIL: Scenes don't have hashes!")
        return False

    if len(mixers_with_hash) == 0:
        print("❌ FAIL: Mixers don't have hashes!")
        return False

    print("✅ PASS: Hashing working correctly")
    print()

    # Final summary
    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("Phase 1b Summary:")
    print(f"  ✓ {len(scenes)} scenes extracted")
    print(f"  ✓ {total_mixer_nodes} mixer nodes created")
    print(f"  ✓ All attributes present and valid")
    print(f"  ✓ AST structure correct")
    print(f"  ✓ Hashing working")
    print()

    return True


if __name__ == "__main__":
    success = test_phase1b()
    exit(0 if success else 1)
