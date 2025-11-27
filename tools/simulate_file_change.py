#!/usr/bin/env python3
"""
Simulate file changes to test DIFF_UPDATE preservation.

This script modifies the XML file to trigger DIFF_UPDATE messages
and verify that expand/collapse state is preserved in the UI.
"""

import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

def modify_track_name(xml_path: Path, track_index: int, new_name: str):
    """Modify a track name in the XML file."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Find all tracks
    tracks = root.findall('.//Tracks/*')

    if track_index >= len(tracks):
        print(f"❌ Track index {track_index} out of range (only {len(tracks)} tracks)")
        return False

    track = tracks[track_index]

    # Find the Name element
    name_elem = track.find('.//Name')
    if name_elem is not None:
        old_name = name_elem.get('Value', '')
        name_elem.set('Value', new_name)

        # Write back to file
        tree.write(xml_path, encoding='utf-8', xml_declaration=True)

        print(f"✅ Modified track {track_index}: '{old_name}' → '{new_name}'")
        print(f"   File saved: {xml_path}")
        return True
    else:
        print(f"❌ Could not find Name element for track {track_index}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python simulate_file_change.py <xml_path> <track_index> <new_name>")
        print("Example: python tools/simulate_file_change.py Example_Project/.vimabl/example_2.xml 3 'Modified Track'")
        sys.exit(1)

    xml_path = Path(sys.argv[1])
    track_index = int(sys.argv[2])
    new_name = sys.argv[3]

    if not xml_path.exists():
        print(f"❌ File not found: {xml_path}")
        sys.exit(1)

    print(f"\n🔧 Simulating file change...")
    print(f"   XML: {xml_path}")
    print(f"   Track: {track_index}")
    print(f"   New name: '{new_name}'")
    print()

    # Make a backup
    backup_path = xml_path.with_suffix('.xml.bak')
    import shutil
    shutil.copy2(xml_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    print()

    # Modify the file
    success = modify_track_name(xml_path, track_index, new_name)

    if success:
        print()
        print("✅ File modified successfully!")
        print()
        print("📊 What should happen in the UI:")
        print(f"   1. XMLFileWatcher detects change")
        print(f"   2. AST server reloads and computes diff")
        print(f"   3. DIFF_UPDATE broadcast to WebSocket clients")
        print(f"   4. Track {track_index} name updates to '{new_name}'")
        print(f"   5. Yellow flash on track {track_index}")
        print(f"   6. ✅ EXPANDED STATE PRESERVED (nodes don't collapse)")
        print()
        print("🔍 Check browser console for:")
        print(f"   [WebSocket] Received DIFF_UPDATE: ...")
        print(f"   [AST Store] Applying X changes to AST")
        print(f"   [AST Store] Modifying track node: track_{track_index}")
        print()
        print(f"💡 To restore: mv {backup_path} {xml_path}")
    else:
        print()
        print("❌ Failed to modify file")
        print(f"   Backup preserved: {backup_path}")

if __name__ == '__main__':
    main()
