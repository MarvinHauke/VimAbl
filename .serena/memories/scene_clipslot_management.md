# Scene and Clip Slot Management Architecture

## Critical Distinctions

### Clip Slot vs Clip
- **ClipSlot**: Fixed grid position `[track_index, scene_index]`, always tied to scenes
  - Cannot be reordered independently from scenes
  - Identified by scene_index within a track
  - Created/removed when scenes are created/removed
  
- **Clip**: Audio/MIDI content, child node of ClipSlot
  - Can be moved, duplicated, or copied between clip slots
  - Carries reference data (MIDI/audio)
  - Can be reordered independently

### Node Hierarchy
```
Track -> ClipSlot (scene_index=N) -> Clip (optional)
```

## Event Handlers and Logic

### Scene Addition (`_handle_scene_added` - lines 749-862)
1. Create new scene node with specified index
2. Shift scene_index of subsequent clip slots in ALL tracks (>= scene_idx → +1)
3. Shift indices of subsequent scenes (+1)
4. Broadcast diff with all changes

### Scene Removal (`_handle_scene_removed` - lines 864-968)
1. Remove scene node at specified index
2. Remove corresponding clip slots from ALL tracks (where scene_index == removed_idx)
3. Shift indices of subsequent scenes (-1)
4. Shift scene_index of subsequent clip slots in ALL tracks (> removed_idx → -1)
5. Broadcast diff with all changes

### Scene Reordered (`_handle_scene_reordered` - lines 971-990)
**DISABLED** - This handler is intentionally disabled because:
1. Cannot reliably identify scenes (scenes can have duplicate/empty names)
2. Scene_added and scene_removed handlers already handle index shifting correctly
3. Processing these events causes duplicate clip slots when scenes have empty/duplicate names
4. Reorder events are sent by Ableton BEFORE scene_added, creating race conditions

### Clip Slot Creation (`_handle_clip_slot_created` - lines 991-1122)
1. **Deduplication**: Check if clip slot with same scene_index already exists in track
   - If exists: Update attributes (modified event)
   - If new: Create and insert at correct position
2. **Insertion logic**: Find correct position by comparing scene_index values
   - Insert before first clip slot with higher scene_index
   - Or insert before mixer node
   - Or append to end
3. No sorting needed - insertion logic maintains order naturally

## Bug History

### Bug #1: Incorrect Reordering (Fixed)
**Problem**: Created `_reorder_clip_slots_in_track()` that sorted clip slots after shifting.
**Why wrong**: Clip slots don't need sorting - insertion logic already positions them correctly.
**Fix**: Removed the reordering function entirely.

### Bug #2: Scene Reorder Handler Duplicates (Fixed)
**Problem**: Scene reorder events used name-based lookup, causing wrong scene to be found when names are duplicate/empty.
**Symptoms**: Multiple clip slots with same scene_index values.
**Root cause**: 
- Reorder events fire BEFORE scene_added
- Handler finds FIRST scene with matching name (wrong scene for duplicates)
- Updates clip slots for wrong scene
- Then scene_added shifts the CORRECT scenes
- Result: Some clip slots shifted twice → duplicates

**Fix**: Disabled scene_reordered handler entirely. Scene identification requires unique IDs, not names.

## Testing Approach

Diagnostic tool: `tools/check_clip_slot_duplicates.py`
- Loads AST and checks for duplicate scene_index values within tracks
- Verifies scene_index values are within valid range [0, max_scene_index]

## Key Insights

1. **No reordering needed**: Clip slots maintain order through insertion logic, not post-hoc sorting
2. **Index shifting is sufficient**: Scene add/remove handlers handle all clip slot index updates
3. **Deduplication is critical**: Clip slot creation handler must check for existing slots
4. **Event timing matters**: Some events (reorder) fire before others (added), creating race conditions
5. **Scene identification**: Must use unique IDs, not names (names can be duplicate/empty)

## Files Modified
- src/server/api.py: Removed _reorder_clip_slots_in_track(), disabled scene_reordered handler
- tools/check_clip_slot_duplicates.py: Created diagnostic tool
