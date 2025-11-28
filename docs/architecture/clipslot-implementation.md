# ClipSlot Matrix Architecture

**Status**: Implemented (Phase 6)
**Date**: 2025-11-25

## Overview

VimAbl implements a full ClipSlot matrix architecture that represents the Session View's clip_slot grid structure. This enables:
- Proper cursor highlighting of empty clip slots
- Real-time detection of clip creation/deletion
- Display of `has_stop_button` property
- Support for active/inactive clips
- Proper scene×track matrix representation

## Architecture

### AST Structure (Option A: ClipSlots Under Tracks)

We utilize a structure where `ClipSlotNode`s are children of `TrackNode`s. This aligns with Ableton's internal XML structure and provides a natural nesting for tree visualization.

```python
ProjectNode
├── TrackNode (index=0)
│   ├── MixerNode
│   ├── DeviceNode[]
│   └── ClipSlotNode[] (one per scene)
│       ├── ClipSlotNode (scene_index=0, has_clip=True, has_stop=True)
│       │   └── ClipNode (midi/audio)
│       ├── ClipSlotNode (scene_index=1, has_clip=False, has_stop=True)
│       └── ClipSlotNode (scene_index=2, has_clip=True, has_stop=False)
├── TrackNode (index=1)
│   └── ClipSlotNode[] ...
└── SceneNode[] (metadata only: name, tempo, color)
```

**Key Benefits:**
- ✅ Matches Ableton's XML structure
- ✅ Easy to find slots by track (`track.clip_slots[scene_idx]`)
- ✅ Clips remain children of their `clip_slot`

## Node Types

### ClipSlotNode

Represents a slot in the Session View grid (can be empty or filled).

```python
@dataclass
class ClipSlotNode(ASTNode):
    node_type: NodeType.CLIP_SLOT
    
    # Attributes
    track_index: int
    scene_index: int
    has_clip: bool
    has_stop_button: bool
    is_playing: bool      # Real-time state
    is_triggered: bool    # Real-time state
    color: int            # Clip/Slot color
```

### ClipNode

Represents the content (MIDI/Audio) within a filled slot. Always a child of `ClipSlotNode`.

## Real-Time Observables

The system monitors real-time state via the `TrackObserver` in the Remote Script.

| Property | Description | Update Frequency |
|----------|-------------|------------------|
| `has_clip` | Detects clip insertion/deletion | Immediate |
| `has_stop_button` | Detects stop button toggle (Cmd+E) | Immediate |
| `playing_status` | 0=Stopped, 1=Playing, 2=Triggered | Immediate |
| `color` | Slot color changes | Immediate |

### Clip Properties (when `has_clip=True`)
- `name`
- `color`
- `muted`
- `looping`

## Web UI Visualization

The Svelte frontend renders the matrix with distinct visual states:

| State | Icon | Style | Meaning |
|-------|------|-------|---------|
| **Playing** | ▶ | Green background | Clip is actively playing |
| **Triggered** | ⏸ | Orange pulse | Clip is queued to launch |
| **Stopped** | ■ | Gray | Clip present, stopped |
| **Empty** | □ | Light gray | Empty slot with stop button |
| **No Stop** | ⊗ | Red text | Empty slot, stop button removed |

## XML Parsing

The `extract_clip_slots` function in `src/parser/clips.py` extracts ALL clip slots from the XML, ensuring the grid is complete even for empty slots.

```python
def extract_clip_slots(track_elem, track_index, num_scenes):
    # 1. Find ClipSlotList
    # 2. Extract all ClipSlot elements
    # 3. Parse HasStop value
    # 4. Fill in missing slots to match num_scenes
    # 5. Return list of slot dicts
```

## Data Flow

1. **XML Load**: `ASTBuilder` creates full `ClipSlotNode` tree.
2. **Live Event**: User triggers clip in Live.
3. **Observer**: `TrackObserver` detects `playing_status` change.
4. **UDP**: Sends `/live/clip_slot/created` (or similar status update).
5. **Server**: `ASTServer._handle_clip_slot_created`:
    - Checks for existing slot (deduplication).
    - Updates attributes (`playing_status`, `has_clip`, etc.).
    - Uses `ClipSlotManager` to insert new slot if needed.
    - Generates and broadcasts `DIFF_UPDATE`.
6. **Frontend**: `astStore.applyDiff()` applies changes to client AST.
7. **UI**: `TreeNode` updates visual state (e.g., orange pulse for triggered).

## Server-Side Management

The `ClipSlotManager` class (`src/server/ast_helpers.py`) encapsulates logic for:
- Finding existing slots by scene index.
- Inserting new slots in the correct order (by `scene_index`).
- Updating slot attributes.
- Creating new `ClipSlotNode` instances with standard IDs.