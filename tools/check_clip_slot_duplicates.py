#!/usr/bin/env python3
"""Check for duplicate or invalid clip slots in the AST."""

import sys
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import load_ableton_xml, build_ast
from src.server import ASTServer
from src.ast.node import NodeType

def check_clip_slots(xml_path: Path):
    """Check for duplicate or invalid clip slots."""
    server = ASTServer()
    server.load_project(xml_path, broadcast=False)

    # Get total scene count
    scenes = [c for c in server.current_ast.children if c.node_type == NodeType.SCENE]
    max_scene_index = len(scenes) - 1 if scenes else -1

    print(f"Total scenes: {len(scenes)}")
    print(f"Scene indices: 0 to {max_scene_index}")
    print()

    # Check each track for clip slot issues
    tracks = [c for c in server.current_ast.children if c.node_type == NodeType.TRACK]

    for track in tracks[:5]:  # Check first 5 tracks
        track_idx = track.attributes.get('index', -1)
        track_name = track.attributes.get('name', 'Unknown')

        # Get all clip slots
        clip_slots = [c for c in track.children if c.node_type == NodeType.CLIP_SLOT]

        print(f"Track {track_idx}: {track_name}")
        print(f"  Total clip slots: {len(clip_slots)}")

        # Group by scene_index
        by_scene_idx = defaultdict(list)
        for slot in clip_slots:
            scene_idx = slot.attributes.get('scene_index', -1)
            by_scene_idx[scene_idx].append(slot.id)

        # Check for duplicates
        for scene_idx in sorted(by_scene_idx.keys()):
            slots = by_scene_idx[scene_idx]
            if len(slots) > 1:
                print(f"  ❌ DUPLICATE at scene_index {scene_idx}: {slots}")
            elif scene_idx > max_scene_index:
                print(f"  ❌ INVALID scene_index {scene_idx} (max is {max_scene_index}): {slots[0]}")
            else:
                print(f"  ✓ scene_index {scene_idx}: {slots[0]}")

        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_clip_slot_duplicates.py <path-to-xml>")
        sys.exit(1)

    xml_path = Path(sys.argv[1])
    check_clip_slots(xml_path)
