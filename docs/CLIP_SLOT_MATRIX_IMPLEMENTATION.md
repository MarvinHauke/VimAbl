# ClipSlot Matrix Implementation Plan

**Status**: Planning
**Date**: 2025-11-17
**Priority**: HIGH

## Overview

Implement a full ClipSlot matrix architecture that properly represents the Session View's clip_slot grid structure. This enables:
- Proper cursor highlighting of empty clip slots
- Real-time detection of clip creation/deletion
- Display of has_stop_button property
- Support for active/inactive clips
- Proper scene×track matrix representation

## Current Architecture Issues

### Problem 1: Missing ClipSlot Structure
**Current**: Clips are stored as a flat array under tracks (`track.clips[]`)
**Issue**: No representation of empty slots or slot position in scene grid
**Impact**: Web UI cannot highlight empty clip slots when selected

### Problem 2: Cursor Events Don't Match AST
**Current**: Cursor sends `/live/cursor/clip_slot <track_idx> <scene_idx> <has_clip>`
**Issue**: Web UI has no corresponding `clip_slot` nodes to highlight
**Impact**: Users select clips in Live but see no visual feedback in web UI

### Problem 3: Scene-Track Relationship Not Explicit
**Current**: Scenes and tracks are separate arrays
**Issue**: No explicit matrix showing which slots exist at each (scene, track) coordinate
**Impact**: Cannot add/remove scenes properly or maintain slot consistency

### Problem 4: Clip Properties Not Tracked
**Current**: Only static clip data from XML
**Issue**: Missing real-time state like `is_playing`, `is_triggered`, `has_stop_button`
**Impact**: Cannot show playback state or stop button configuration

## Architecture Goals

1. **Matrix Structure**: Create explicit scene×track ClipSlot matrix
2. **Empty Slots**: Represent ALL slots, not just filled ones
3. **Real-Time State**: Track playback state, trigger state, stop button state
4. **Cursor Highlighting**: Enable web UI to highlight any selected slot
5. **Scene Scalability**: Easy to add/remove scenes and update all track clip_slots
6. **Backward Compatibility**: Option to maintain old `clips[]` array

## Proposed AST Structure

### Option A: ClipSlots Under Tracks (Recommended)

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

**Pros:**
- ✅ Matches Ableton's XML structure
- ✅ Easy to find slots by track (track.clip_slots[scene_idx])
- ✅ Natural nesting for tree visualization
- ✅ Clips remain children of their clip_slot

**Cons:**
- ⚠️ Scene information is separate (but scenes are just metadata)

### Option B: Scenes Contain ClipSlots (Grid-First)

```python
ProjectNode
├── TrackNode[] (devices, mixer only)
└── SceneNode[]
    ├── SceneNode (index=0)
    │   └── ClipSlotNode[] (one per track)
    │       ├── ClipSlotNode (track_index=0, has_clip=True)
    │       └── ClipSlotNode (track_index=1, has_clip=False)
    └── SceneNode (index=1) ...
```

**Pros:**
- ✅ Explicit scene×track grid structure
- ✅ Easy to add/remove entire scenes

**Cons:**
- ❌ Doesn't match XML structure
- ❌ Harder to find slots by track
- ❌ Clips separated from track context

**Decision**: Use **Option A** (ClipSlots under tracks)

## Node Type Definitions

### ClipSlotNode

```python
@dataclass
class ClipSlotNode(ASTNode):
    """
    Node representing a clip slot (can be empty or contain a clip).

    Attributes:
        track_index: int - Parent track index
        scene_index: int - Scene row index
        has_clip: bool - Whether slot contains a clip
        has_stop_button: bool - Whether slot has stop button
        is_playing: bool - Clip playback state (real-time)
        is_triggered: bool - Clip trigger state (real-time)
    """
    def __init__(self, track_index: int, scene_index: int, **kwargs):
        super().__init__(node_type=NodeType.CLIP_SLOT, **kwargs)
        self.attributes['track_index'] = track_index
        self.attributes['scene_index'] = scene_index
        self.attributes['has_clip'] = False
        self.attributes['has_stop_button'] = True  # Default
        self.attributes['is_playing'] = False
        self.attributes['is_triggered'] = False
```

### Updated ClipNode

```python
@dataclass
class ClipNode(ASTNode):
    """
    Node representing a MIDI or audio clip.
    Now always a child of ClipSlotNode.

    Attributes remain the same:
        name, clip_type, start_time, end_time, loop settings, etc.
    """
```

## Implementation Phases

### Phase 6a: Add CLIP_SLOT Node Type

**Files to modify:**
- `src/ast/node.py`

**Changes:**
1. Add `CLIP_SLOT = "clip_slot"` to `NodeType` enum
2. Create `ClipSlotNode` class
3. Update `__init__.py` exports

**Testing:**
- Import `ClipSlotNode` successfully
- Create test instances
- Verify attributes

**Status**: Ready to implement

---

### Phase 6b: Update XML Parser for ClipSlots

**Files to modify:**
- `src/parser/clips.py` - Refactor `extract_clips()` → `extract_clip_slots()`
- `src/parser/ast_builder.py` - Call new extractor
- `src/parser/scenes.py` - Track number of scenes

**Changes:**

#### `clips.py::extract_clip_slots()`

```python
def extract_clip_slots(track_elem: ET.Element, track_index: int, num_scenes: int) -> List[Dict[str, Any]]:
    """
    Extract ALL clip slots from a track (both empty and filled).

    Args:
        track_elem: XML element representing a track
        track_index: Index of this track in the song
        num_scenes: Total number of scenes in the project

    Returns:
        List of clip_slot dicts (one per scene)
        Each dict has:
        {
            'scene_index': int,
            'has_clip': bool,
            'has_stop_button': bool,
            'clip': {...} or None  # Clip data if has_clip=True
        }
    """
    clip_slots = []

    # Find ClipSlotList
    clip_slot_list = track_elem.find('.//ClipSlotList')
    if clip_slot_list is None:
        # No clip slot list (e.g., return track, master track)
        # Return empty list
        return []

    # Get all ClipSlot elements
    slot_elements = clip_slot_list.findall('.//ClipSlot')

    for scene_index, slot_elem in enumerate(slot_elements):
        # Extract has_stop_button (default True)
        has_stop_elem = slot_elem.find('./HasStop')
        has_stop_button = True  # Default
        if has_stop_elem is not None:
            has_stop_button = has_stop_elem.get('Value', 'true').lower() == 'true'

        # Check if slot has a clip
        clip_info = _extract_clip_from_slot(slot_elem)

        slot_data = {
            'scene_index': scene_index,
            'track_index': track_index,
            'has_clip': clip_info is not None,
            'has_stop_button': has_stop_button,
            'clip': clip_info  # None if empty, clip data if filled
        }

        clip_slots.append(slot_data)

    # Verify we have the expected number of slots
    # (should match num_scenes, but XML might have fewer)
    while len(clip_slots) < num_scenes:
        # Add empty slots for missing scenes
        clip_slots.append({
            'scene_index': len(clip_slots),
            'track_index': track_index,
            'has_clip': False,
            'has_stop_button': True,
            'clip': None
        })

    return clip_slots
```

#### `ast_builder.py` updates

```python
def build_ast(root):
    # ... existing code ...

    # Extract scenes FIRST (to get total count)
    scenes = extract_scenes(root)
    num_scenes = len(scenes)

    # Extract tracks
    tracks = extract_tracks(root)

    # Enrich each track with clip_slots (instead of clips)
    for i, track_elem in enumerate(track_elements):
        if i < len(tracks):
            # Extract devices
            devices = extract_devices(track_elem)
            tracks[i]['devices'] = devices

            # Extract clip_slots (replaces clips)
            if tracks[i]['type'] != 'return':
                clip_slots = extract_clip_slots(track_elem, i, num_scenes)
                tracks[i]['clip_slots'] = clip_slots

            # Extract mixer
            mixer = extract_mixer_from_track(track_elem)
            tracks[i]['mixer'] = mixer

    return {
        "tracks": tracks,
        "scenes": scenes,
        "file_refs": extract_file_refs(root),
    }
```

**Testing:**
- Parse example project
- Verify all tracks have `clip_slots` array
- Verify `len(clip_slots) == num_scenes` for each track
- Check empty slots have `has_clip=False`
- Check filled slots have `has_clip=True` and clip data
- Verify `has_stop_button` property parsed correctly

**Status**: Ready to implement after Phase 6a

---

### Phase 6c: Update AST Builder to Create ClipSlotNodes

**Files to modify:**
- `src/server/api.py` - `_build_node_tree()` method

**Changes:**

```python
def _build_node_tree(self, raw_ast: Dict[str, Any], root_elem) -> ProjectNode:
    """Build typed node tree from raw dict AST."""
    # ... existing code for project, tracks, devices ...

    # Build clip_slot nodes under each track
    for track_dict in raw_ast.get('tracks', []):
        track_node = # ... existing track node creation ...

        # Create ClipSlotNode for each slot
        for slot_dict in track_dict.get('clip_slots', []):
            slot_node = ClipSlotNode(
                track_index=slot_dict['track_index'],
                scene_index=slot_dict['scene_index'],
                id=f"slot_{slot_dict['track_index']}_{slot_dict['scene_index']}"
            )
            slot_node.attributes['has_clip'] = slot_dict['has_clip']
            slot_node.attributes['has_stop_button'] = slot_dict['has_stop_button']
            slot_node.attributes['is_playing'] = False  # Will be updated by observers
            slot_node.attributes['is_triggered'] = False  # Will be updated by observers

            # If slot has a clip, create ClipNode as child
            if slot_dict['clip'] is not None:
                clip_data = slot_dict['clip']
                clip_node = ClipNode(
                    name=clip_data['name'],
                    clip_type=clip_data['type'],
                    id=f"clip_{slot_dict['track_index']}_{slot_dict['scene_index']}"
                )
                # Copy clip attributes
                for key, value in clip_data.items():
                    if key not in ['name', 'type']:
                        clip_node.attributes[key] = value

                slot_node.add_child(clip_node)

            track_node.add_child(slot_node)

    # ... rest of method ...
```

**Testing:**
- Build AST from example project
- Verify ClipSlotNode instances created
- Verify empty slots have no children
- Verify filled slots have ClipNode child
- Check `track.children` includes clip_slots
- Verify node IDs are unique

**Status**: Ready to implement after Phase 6b

---

### Phase 6d: Update Web UI to Display ClipSlots

**Files to modify:**
- `src/web/frontend/src/lib/components/TreeNode.svelte`
- `src/web/frontend/src/lib/stores/cursor.svelte.ts`

**Changes:**

#### TreeNode.svelte - Add clip_slot rendering

```typescript
// Existing node type detection
let nodeIcon = $derived(() => {
    switch (node.node_type) {
        case 'clip_slot':
            // Different icons for empty vs filled slots
            if (node.attributes?.has_clip) {
                return '🎵';  // Filled slot
            } else if (node.attributes?.has_stop_button === false) {
                return '⊘';  // No stop button
            } else {
                return '⏹️';  // Empty slot with stop button
            }
        case 'clip':
            return node.attributes?.clip_type === 'midi' ? '🎹' : '🎤';
        // ... existing cases ...
    }
});

// Highlight logic for clip slots
let isHighlightedClipSlot = $derived(
    node.node_type === 'clip_slot' &&
    cursorStore.highlightedSlot !== null &&
    node.attributes?.track_index === cursorStore.highlightedSlot.track &&
    node.attributes?.scene_index === cursorStore.highlightedSlot.scene
);

// CSS class for clip slot state
let clipSlotStateClass = $derived(() => {
    if (node.node_type !== 'clip_slot') return '';

    const attrs = node.attributes;
    if (attrs?.is_playing) return 'clip-playing';
    if (attrs?.is_triggered) return 'clip-triggered';
    if (attrs?.has_clip) return 'clip-filled';
    if (!attrs?.has_stop_button) return 'clip-no-stop';
    return 'clip-empty';
});
```

#### CSS for clip slot states

```css
/* In TreeNode.svelte <style> */

/* Highlighted clip slot (cursor selection) */
.highlighted-slot {
    background-color: rgba(251, 191, 36, 0.2);
    border-left: 3px solid #fbbf24;
    transition: all 0.15s ease;
}

/* Clip playing state */
.clip-playing {
    background-color: rgba(34, 197, 94, 0.15);
    border-left: 2px solid #22c55e;
}

/* Clip triggered (will play soon) */
.clip-triggered {
    background-color: rgba(251, 191, 36, 0.15);
    border-left: 2px solid #fbbf24;
    animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

/* Filled slot (has clip but not playing) */
.clip-filled {
    /* Default - no special styling */
}

/* Empty slot with stop button */
.clip-empty {
    opacity: 0.6;
}

/* Empty slot without stop button */
.clip-no-stop {
    opacity: 0.4;
    font-style: italic;
}
```

**Testing:**
- Open web UI
- Verify clip_slot nodes appear under tracks
- Check icons show correctly (filled vs empty)
- Select a clip slot in Live
- Verify highlight appears in web UI
- Check different slot states render correctly

**Status**: Ready to implement after Phase 6c

---

### Phase 6e: Update Clip Observers for Real-Time State

**Files to modify:**
- `src/remote_script/observers.py` - Update `TrackObserver`
- `src/web/frontend/src/lib/stores/ast-updater.ts` - Add clip_slot event handlers

**Changes:**

#### observers.py - Enhance clip_slot observer

Currently observes `has_clip` changes. Need to also track:
- `is_playing` state
- `is_triggered` state

```python
class TrackObserver:
    def _observe_clip_slots(self):
        """Set up listeners for all clip slots on this track."""
        try:
            for scene_idx, clip_slot in enumerate(self.track.clip_slots):
                # Store initial state
                has_clip = clip_slot.has_clip
                self.clip_slot_states[(self.track_index, scene_idx)] = {
                    'has_clip': has_clip,
                    'is_playing': clip_slot.is_playing if has_clip else False,
                    'is_triggered': clip_slot.is_triggered if has_clip else False,
                }

                # Create callbacks for this slot
                if scene_idx not in self.clip_slot_callbacks:
                    self.clip_slot_callbacks[scene_idx] = {
                        'has_clip': self._create_has_clip_callback(scene_idx),
                        'is_playing': self._create_is_playing_callback(scene_idx),
                        'is_triggered': self._create_is_triggered_callback(scene_idx),
                    }

                # Add has_clip listener (already exists)
                callback = self.clip_slot_callbacks[scene_idx]['has_clip']
                if clip_slot.has_clip_has_listener(callback):
                    clip_slot.remove_has_clip_listener(callback)
                clip_slot.add_has_clip_listener(callback)

                # Add is_playing listener
                if has_clip:
                    callback = self.clip_slot_callbacks[scene_idx]['is_playing']
                    if clip_slot.is_playing_has_listener(callback):
                        clip_slot.remove_is_playing_listener(callback)
                    clip_slot.add_is_playing_listener(callback)

                    # Add is_triggered listener
                    callback = self.clip_slot_callbacks[scene_idx]['is_triggered']
                    if clip_slot.is_triggered_has_listener(callback):
                        clip_slot.remove_is_triggered_listener(callback)
                    clip_slot.add_is_triggered_listener(callback)

            self.log(f"Track {self.track_index}: Observing {len(self.track.clip_slots)} clip slots")
        except Exception as e:
            self.log(f"Error observing clip slots: {e}")

    def _create_is_playing_callback(self, scene_idx):
        """Create callback for is_playing listener."""
        def callback():
            self._on_clip_playing_changed(scene_idx)
        return callback

    def _create_is_triggered_callback(self, scene_idx):
        """Create callback for is_triggered listener."""
        def callback():
            self._on_clip_triggered_changed(scene_idx)
        return callback

    def _on_clip_playing_changed(self, scene_idx: int):
        """Called when clip playback state changes."""
        try:
            clip_slot = self.track.clip_slots[scene_idx]
            if clip_slot.has_clip:
                is_playing = clip_slot.is_playing
                self.sender.send_event("/live/clip_slot/playing",
                                      self.track_index, scene_idx, is_playing)
                self.log(f"Clip slot [{self.track_index},{scene_idx}] playing: {is_playing}")
        except Exception as e:
            self.log(f"Error handling clip playing change: {e}")

    def _on_clip_triggered_changed(self, scene_idx: int):
        """Called when clip trigger state changes."""
        try:
            clip_slot = self.track.clip_slots[scene_idx]
            if clip_slot.has_clip:
                is_triggered = clip_slot.is_triggered
                self.sender.send_event("/live/clip_slot/triggered",
                                      self.track_index, scene_idx, is_triggered)
                self.log(f"Clip slot [{self.track_index},{scene_idx}] triggered: {is_triggered}")
        except Exception as e:
            self.log(f"Error handling clip triggered change: {e}")
```

#### New OSC Events

Add to `src/remote_script/osc.py`:

```python
def build_clip_slot_playing(track_idx: int, scene_idx: int, is_playing: bool) -> tuple:
    """Build clip_slot playing state event."""
    return ("/live/clip_slot/playing", track_idx, scene_idx, is_playing)

def build_clip_slot_triggered(track_idx: int, scene_idx: int, is_triggered: bool) -> tuple:
    """Build clip_slot triggered state event."""
    return ("/live/clip_slot/triggered", track_idx, scene_idx, is_triggered)
```

#### ast-updater.ts - Handle new events

```typescript
export function updateFromLiveEvent(ast: ASTNode, eventPath: string, args: any[]): boolean {
    switch (eventPath) {
        case '/live/clip_slot/playing': {
            const [trackIdx, sceneIdx, isPlaying] = args;
            const clipSlot = findClipSlot(ast, trackIdx, sceneIdx);
            if (clipSlot) {
                clipSlot.attributes.is_playing = isPlaying !== 0;
                return true;
            }
            return false;
        }

        case '/live/clip_slot/triggered': {
            const [trackIdx, sceneIdx, isTriggered] = args;
            const clipSlot = findClipSlot(ast, trackIdx, sceneIdx);
            if (clipSlot) {
                clipSlot.attributes.is_triggered = isTriggered !== 0;
                return true;
            }
            return false;
        }

        // ... existing cases ...
    }
}

function findClipSlot(ast: ASTNode, trackIdx: number, sceneIdx: number): ASTNode | null {
    // Find track
    const track = findTrack(ast, trackIdx);
    if (!track) return null;

    // Find clip_slot with matching scene_index
    return track.children.find(
        child => child.node_type === 'clip_slot' &&
                 child.attributes?.scene_index === sceneIdx
    ) || null;
}
```

**Testing:**
- Trigger a clip in Live
- Verify `/live/clip_slot/playing` event sent
- Check web UI shows green highlight
- Stop clip
- Verify playing state clears
- Test clip triggering (before playback starts)
- Verify yellow pulse animation

**Status**: Ready to implement after Phase 6d

---

### Phase 6f: Scene Add/Remove Support

**Future enhancement** - When scenes are added/removed:

1. **Remote Script**: Send `/live/scene/added <scene_idx>` or `/live/scene/removed <scene_idx>`
2. **AST Updater**: Add/remove ClipSlotNode to ALL tracks at that scene_index
3. **Web UI**: Render new slots or remove deleted slots

**Not in initial scope** - Can be added in Phase 7

---

### Phase 6g: Documentation

**Files to create/update:**
- `docs/architecture/clip_slot_matrix.md` - Architecture documentation
- `docs/CHANGELOG.md` - Add entry for this feature
- `TODO.md` - Update with Phase 6 completion status

**Content:**
- Architecture diagrams
- XML → AST mapping
- Observer event flow
- Web UI rendering logic
- Testing procedures

**Status**: Create after all phases complete

---

## Testing Strategy

### Unit Tests

```python
# tests/test_clip_slot_parser.py
def test_extract_clip_slots_all_empty():
    """Test extracting clip slots when all are empty."""
    ...

def test_extract_clip_slots_mixed():
    """Test extracting clip slots with some filled."""
    ...

def test_has_stop_button_parsing():
    """Test has_stop_button property parsed correctly."""
    ...
```

### Integration Tests

```python
# tests/test_clip_slot_ast.py
def test_clip_slot_nodes_created():
    """Test ClipSlotNode instances created in AST."""
    ...

def test_clip_slot_matrix_complete():
    """Test all tracks have clip_slots for all scenes."""
    ...
```

### Manual Testing Checklist

- [ ] Load project with clips
- [ ] Verify clip_slots appear in web UI
- [ ] Select empty slot in Live → Check highlight in UI
- [ ] Select filled slot in Live → Check highlight in UI
- [ ] Trigger clip → Check green playing state
- [ ] Stop clip → Check state clears
- [ ] Create new clip → Check `/live/clip/added` event
- [ ] Delete clip → Check `/live/clip/removed` event
- [ ] Check has_stop_button display
- [ ] Test with large project (50+ scenes)

## Backward Compatibility

### Option 1: Maintain Both Structures (Recommended for transition)

Keep `track.clips[]` array AND add `track.clip_slots[]`:

```python
tracks[i]['clips'] = [...]  # Flat array (old)
tracks[i]['clip_slots'] = [...]  # Matrix (new)
```

Gradually migrate consumers to use `clip_slots`, then remove `clips` in v2.0.

### Option 2: Hard Cut-Over

Remove `clips[]` entirely, force all consumers to update.

**Recommendation**: Use Option 1 for smoother migration.

## Performance Considerations

### Memory Impact

- **Before**: ~100 bytes per clip × N clips
- **After**: ~100 bytes per clip_slot × (N_tracks × N_scenes)

For typical project (32 tracks, 8 scenes):
- Before: Variable (depends on clips)
- After: 256 clip_slots × 100 bytes = ~25 KB

**Acceptable** - Trivial memory overhead for desktop app.

### Rendering Impact

- TreeView now renders clip_slots (always visible)
- Before: Only rendered clips (collapsed by default)
- After: More nodes to render initially

**Mitigation**:
- Virtual scrolling (already planned in Phase 3c)
- Lazy-load clip_slot children
- Collapse tracks by default

## Migration Plan

1. **Phase 6a-6c**: Implement core clip_slot infrastructure
2. **Phase 6d**: Update web UI (parallel to old structure)
3. **Phase 6e**: Add real-time observers
4. **Verification**: Test with real projects
5. **Deprecation**: Mark `clips[]` as deprecated
6. **v2.0**: Remove `clips[]` entirely

## Success Criteria

- [ ] All clip_slots appear in AST (empty and filled)
- [ ] Web UI highlights selected clip_slot (empty or filled)
- [ ] Real-time playback state updates in UI
- [ ] Scene×Track matrix is complete and consistent
- [ ] Performance is acceptable (no lag with 50+ scenes)
- [ ] Backward compatibility maintained (if Option 1 chosen)
- [ ] Documentation is complete and accurate

## Timeline Estimate

- **Phase 6a**: 30 minutes (node type definition)
- **Phase 6b**: 2 hours (XML parser refactor)
- **Phase 6c**: 1 hour (AST builder update)
- **Phase 6d**: 2 hours (Web UI rendering)
- **Phase 6e**: 2 hours (Real-time observers)
- **Phase 6g**: 1 hour (Documentation)

**Total**: ~8-9 hours of implementation

## Next Steps

1. Review this plan with user
2. Get approval for architecture choice (Option A confirmed)
3. Update TODO.md with Phase 6 tasks
4. Begin implementation in order: 6a → 6b → 6c → 6d → 6e → 6g
5. Test thoroughly at each phase
6. Document learnings as we go

## Related Documents

- `docs/architecture/websocket-ast.md` - WebSocket architecture
- `docs/user-guide/web-treeviewer.md` - Web UI user guide
- `docs/OSC_PROTOCOL.md` - OSC event protocol
- `TODO.md` - Project roadmap
