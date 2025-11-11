#!/usr/bin/env python3
"""
Interactive inspector for Phase 1b: Scenes & Mixer

Usage: python3 inspect_phase1b.py
"""

import json
from pathlib import Path
from src.server import ASTServer
from src.ast import NodeType


def main():
    """Interactive inspection of Phase 1b features."""

    # Load project
    server = ASTServer()
    project_path = Path("Example_Project/example.als")

    print("Loading project...")
    server.load_project(project_path)

    while True:
        print("\n" + "=" * 60)
        print("PHASE 1B INSPECTOR")
        print("=" * 60)
        print("\n1. Show all scenes")
        print("2. Show scene by index")
        print("3. Show all tracks with mixer info")
        print("4. Show mixer for specific track")
        print("5. Export scene JSON")
        print("6. Export mixer JSON")
        print("7. Compare scenes (tempo differences)")
        print("8. Show tracks by mixer state (muted/soloed)")
        print("9. Exit")
        print()

        choice = input("Choose option (1-9): ").strip()

        if choice == "1":
            # Show all scenes
            scenes = server.search_visitor.find_by_type(server.current_ast, NodeType.SCENE)
            print(f"\nFound {len(scenes)} scenes:\n")
            for scene in scenes:
                name = scene.attributes.get('name', '(unnamed)')
                idx = scene.attributes.get('index')
                tempo = scene.attributes.get('tempo')
                tempo_en = scene.attributes.get('is_tempo_enabled')
                print(f"  Scene {idx}: '{name}' - Tempo: {tempo} BPM {'(enabled)' if tempo_en else '(disabled)'}")

        elif choice == "2":
            # Show specific scene
            idx = input("Enter scene index: ").strip()
            try:
                idx = int(idx)
                scenes = server.search_visitor.find_by_type(server.current_ast, NodeType.SCENE)
                scene = next((s for s in scenes if s.attributes.get('index') == idx), None)
                if scene:
                    print(f"\nScene {idx} details:")
                    for key, val in scene.attributes.items():
                        print(f"  {key:25s}: {val}")
                else:
                    print(f"Scene {idx} not found!")
            except ValueError:
                print("Invalid index!")

        elif choice == "3":
            # Show all tracks with mixer
            tracks = server.search_visitor.find_by_type(server.current_ast, NodeType.TRACK)
            print(f"\nFound {len(tracks)} tracks:\n")
            for track in tracks[:10]:  # First 10 tracks
                idx = track.attributes.get('index')
                name = track.attributes.get('name', '(unnamed)')
                mixer = next((c for c in track.children if c.node_type == NodeType.MIXER), None)
                if mixer:
                    vol = mixer.attributes.get('volume', 1.0)
                    pan = mixer.attributes.get('pan', 0.0)
                    muted = mixer.attributes.get('is_muted', False)
                    soloed = mixer.attributes.get('is_soloed', False)
                    status = []
                    if muted: status.append("M")
                    if soloed: status.append("S")
                    status_str = f"[{'/'.join(status)}]" if status else ""
                    print(f"  Track {idx:2d}: '{name:20s}' Vol: {vol:.2f} Pan: {pan:+.2f} {status_str}")

        elif choice == "4":
            # Show specific track mixer
            idx = input("Enter track index: ").strip()
            try:
                idx = int(idx)
                tracks = server.search_visitor.find_by_type(server.current_ast, NodeType.TRACK)
                track = next((t for t in tracks if t.attributes.get('index') == idx), None)
                if track:
                    mixer = next((c for c in track.children if c.node_type == NodeType.MIXER), None)
                    if mixer:
                        print(f"\nTrack {idx} mixer details:")
                        for key, val in mixer.attributes.items():
                            if key == 'sends':
                                print(f"  {key:25s}:")
                                for send in val:
                                    print(f"    Send {send['index']}: level={send['level']:.3f}, active={send['is_active']}")
                            else:
                                print(f"  {key:25s}: {val}")
                    else:
                        print(f"No mixer found for track {idx}!")
                else:
                    print(f"Track {idx} not found!")
            except ValueError:
                print("Invalid index!")

        elif choice == "5":
            # Export scene JSON
            scenes = server.search_visitor.find_by_type(server.current_ast, NodeType.SCENE)
            scene_data = [s.attributes for s in scenes]
            filename = "scenes_export.json"
            with open(filename, 'w') as f:
                json.dump(scene_data, f, indent=2)
            print(f"\n✓ Exported {len(scenes)} scenes to {filename}")

        elif choice == "6":
            # Export mixer JSON
            tracks = server.search_visitor.find_by_type(server.current_ast, NodeType.TRACK)
            mixer_data = []
            for track in tracks:
                mixer = next((c for c in track.children if c.node_type == NodeType.MIXER), None)
                if mixer:
                    mixer_data.append({
                        'track_index': track.attributes.get('index'),
                        'track_name': track.attributes.get('name'),
                        **mixer.attributes
                    })
            filename = "mixer_export.json"
            with open(filename, 'w') as f:
                json.dump(mixer_data, f, indent=2)
            print(f"\n✓ Exported {len(mixer_data)} mixer settings to {filename}")

        elif choice == "7":
            # Compare scene tempos
            scenes = server.search_visitor.find_by_type(server.current_ast, NodeType.SCENE)
            tempos = {}
            for scene in scenes:
                tempo = scene.attributes.get('tempo')
                if tempo not in tempos:
                    tempos[tempo] = []
                tempos[tempo].append(scene.attributes.get('index'))

            print(f"\nTempo distribution across {len(scenes)} scenes:")
            for tempo in sorted(tempos.keys()):
                scene_list = ", ".join(map(str, tempos[tempo]))
                print(f"  {tempo} BPM: Scenes {scene_list}")

        elif choice == "8":
            # Show tracks by mixer state
            tracks = server.search_visitor.find_by_type(server.current_ast, NodeType.TRACK)
            muted = []
            soloed = []
            for track in tracks:
                mixer = next((c for c in track.children if c.node_type == NodeType.MIXER), None)
                if mixer:
                    idx = track.attributes.get('index')
                    name = track.attributes.get('name', '(unnamed)')
                    if mixer.attributes.get('is_muted'):
                        muted.append(f"Track {idx}: '{name}'")
                    if mixer.attributes.get('is_soloed'):
                        soloed.append(f"Track {idx}: '{name}'")

            print(f"\nMuted tracks ({len(muted)}):")
            for m in muted:
                print(f"  {m}")

            print(f"\nSoloed tracks ({len(soloed)}):")
            for s in soloed:
                print(f"  {s}")

        elif choice == "9":
            print("\nGoodbye!")
            break

        else:
            print("\nInvalid choice!")


if __name__ == "__main__":
    main()
