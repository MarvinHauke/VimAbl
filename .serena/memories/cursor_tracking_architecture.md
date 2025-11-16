# Cursor Tracking Architecture - Ultra-Low Latency Design

**Date**: 2025-11-16  
**Status**: Planning  
**Priority**: Low latency is critical

## Overview

Track cursor/selection state across all Ableton Live views with minimal latency (<20ms target). Differentiate between:
1. **Session View** - Track + Clip slot selection
2. **Arrangement View** - Timeline playhead position
3. **Detail View** - Clip editor and Device editor focus

## Latency Requirements

**Target**: < 20ms end-to-end (Live selection change → UI highlight)

**Breakdown**:
- Live API listener callback: ~1ms
- UDP send (localhost): ~0.5ms
- UDP → WebSocket broadcast: ~2ms
- WebSocket → Browser: ~2-5ms
- React/render: ~5-10ms
- **Total**: ~10-18ms ✅

## Architecture - Direct UDP Path (No Bridge)

```
[Ableton Live Remote Script]
  └─ CursorObserver
      ├─ song.view.selected_track_has_listener
      ├─ song.view.selected_scene_has_listener  
      ├─ song.view.highlighted_clip_slot_has_listener
      ├─ song.view.detail_clip_has_listener
      └─ song.current_song_time_has_listener (arrangement)
           │
           ▼ UDP/OSC (localhost:9002) - immediate send
           │
[Existing UDP Listener in main.py]
  └─ udp_event_callback()
      ├─ Receives cursor events
      ├─ Updates in-memory cursor state
      └─ Broadcasts via WebSocket
           │
           ▼ WebSocket (port 8765)
           │
[Svelte UI]
  └─ Cursor Store (Svelte 5 runes)
      ├─ Tracks current selection
      ├─ Highlights selected node in TreeView
      └─ Smooth cursor animation
```

### Why No Bridge Layer?

**Rejected Architecture**: Separate UDP-to-WS bridge
- **Extra latency**: +5-10ms for another process
- **Extra complexity**: Another service to manage
- **No benefit**: Our UDP listener already broadcasts to WS

**Chosen Architecture**: Reuse existing UDP→WS pipeline
- **Zero extra latency**: Already optimized path
- **Simpler**: One less moving part
- **Proven**: Same path as parameter updates (~10ms latency)

## Live API - Available Selection Properties

### Song.View Object

```python
view = self.song().view

# Session View Selection
selected_track = view.selected_track          # get/set/observe
selected_scene = view.selected_scene          # get/set/observe  
highlighted_clip_slot = view.highlighted_clip_slot  # get/set (no observe!)

# Detail View Selection
detail_clip = view.detail_clip                # get/set/observe
selected_parameter = view.selected_parameter  # observe only
selected_chain = view.selected_chain          # get/set/observe

# Arrangement View
current_song_time = self.song().current_song_time  # observe for playhead
```

### Key Discovery: highlighted_clip_slot Limitation

**Problem**: `highlighted_clip_slot` does NOT support `has_listener`!

**Workaround Options**:
1. **Poll in update_display()**: Called ~60 Hz, acceptable latency (~16ms)
2. **Track selection indirectly**: Use `selected_track` + `selected_scene` to infer slot
3. **Hybrid approach**: Observe track/scene, poll highlighted_clip_slot

**Recommendation**: Use hybrid approach for Session View

## Implementation Plan - Phase by Phase

### Phase 1: Session View Cursor (Priority 1)

**What to Track**:
- Selected track index
- Selected scene index
- Highlighted clip slot (track_idx, scene_idx)
- Clip slot state (has_clip, is_playing, is_triggered)

**Implementation**:

```python
class SessionCursorObserver:
    def __init__(self, song, sender):
        self.song = song
        self.sender = sender
        self.view = song.view
        self.last_clip_slot = (None, None)  # (track_idx, scene_idx)
        
        # Add observers
        self.view.add_selected_track_listener(self._on_track_changed)
        self.view.add_selected_scene_listener(self._on_scene_changed)
    
    def update(self):
        """Called from LiveState.update_display() at ~60 Hz"""
        # Poll highlighted_clip_slot (no observer available)
        slot = self.view.highlighted_clip_slot
        if slot:
            track_idx = list(self.song.tracks).index(slot.canonical_parent)
            scene_idx = list(self.song.scenes).index(
                self.song.scenes[0] if slot in self.song.scenes[0].clip_slots else ...
            )
            
            current = (track_idx, scene_idx)
            if current != self.last_clip_slot:
                self._send_cursor_event(track_idx, scene_idx, slot)
                self.last_clip_slot = current
    
    def _on_track_changed(self):
        track = self.view.selected_track
        track_idx = list(self.song.tracks).index(track)
        self.sender.send_event("/live/cursor/track", track_idx)
    
    def _on_scene_changed(self):
        scene = self.view.selected_scene
        scene_idx = list(self.song.scenes).index(scene)
        self.sender.send_event("/live/cursor/scene", scene_idx)
    
    def _send_cursor_event(self, track_idx, scene_idx, slot):
        has_clip = slot.has_clip
        is_playing = slot.is_playing if has_clip else False
        is_triggered = slot.is_triggered if has_clip else False
        
        self.sender.send_event("/live/cursor/clip_slot", 
            track_idx, scene_idx, has_clip, is_playing, is_triggered)
```

**UDP Event Format**:
```python
# Track selection
/live/seq <seq> <time> /live/cursor/track <track_idx>

# Scene selection
/live/seq <seq> <time> /live/cursor/scene <scene_idx>

# Clip slot highlight
/live/seq <seq> <time> /live/cursor/clip_slot <track_idx> <scene_idx> <has_clip> <is_playing> <is_triggered>
```

### Phase 2: Arrangement View Cursor (Priority 2)

**What to Track**:
- Playhead position (beats)
- Loop start/end positions
- Follow mode state

**Implementation**:

```python
class ArrangementCursorObserver:
    def __init__(self, song, sender):
        self.song = song
        self.sender = sender
        self.last_time = 0.0
        
        # Observe playhead (throttled to avoid flooding)
        self.song.add_current_song_time_listener(self._on_time_changed)
    
    def _on_time_changed(self):
        """Called on every playhead move - needs throttling!"""
        current_time = self.song.current_song_time
        
        # Throttle: only send if moved by at least 0.1 beats
        if abs(current_time - self.last_time) >= 0.1:
            self.sender.send_event("/live/cursor/playhead", current_time)
            self.last_time = current_time
```

**UDP Event Format**:
```python
/live/seq <seq> <time> /live/cursor/playhead <beat_position>
```

### Phase 3: Detail View Cursor (Priority 3)

**What to Track**:
- Active clip in detail view
- Selected device
- Selected parameter

**Implementation**:

```python
class DetailCursorObserver:
    def __init__(self, song, sender):
        self.song = song
        self.sender = sender
        self.view = song.view
        
        # Observe detail view changes
        self.view.add_detail_clip_listener(self._on_clip_changed)
        self.view.add_selected_parameter_listener(self._on_param_changed)
    
    def _on_clip_changed(self):
        clip = self.view.detail_clip
        if clip:
            # Find clip slot
            track_idx = list(self.song.tracks).index(clip.canonical_parent.canonical_parent)
            scene_idx = # ... find scene index
            self.sender.send_event("/live/cursor/detail_clip", track_idx, scene_idx)
    
    def _on_param_changed(self):
        param = self.view.selected_parameter
        if param:
            # Send parameter selection
            self.sender.send_event("/live/cursor/parameter", 
                param.name, param.value)
```

## Latency Optimizations

### 1. Zero-Copy Event Sending

**Current (parameter events)**:
```python
def trigger(self, event_key, value, callback, min_interval_ms=50):
    # Debounces, adds latency
```

**For Cursor (immediate)**:
```python
def send_cursor_event(self, path, *args):
    # No debouncing - send immediately
    self.sender.send_event(path, *args)
```

### 2. Efficient Clip Slot Lookup

**Slow (O(n²))**:
```python
for track_idx, track in enumerate(self.song.tracks):
    for scene_idx, slot in enumerate(track.clip_slots):
        if slot == highlighted_slot:
            return (track_idx, scene_idx)
```

**Fast (O(1) with caching)**:
```python
# Cache slot → (track_idx, scene_idx) mapping
self.slot_index_cache = {}

def get_slot_indices(self, slot):
    if slot not in self.slot_index_cache:
        # Build on first access
        track = slot.canonical_parent
        track_idx = list(self.song.tracks).index(track)
        scene_idx = list(track.clip_slots).index(slot)
        self.slot_index_cache[slot] = (track_idx, scene_idx)
    return self.slot_index_cache[slot]
```

### 3. Selective Update Display Polling

**Problem**: `update_display()` called at 60 Hz (16ms intervals)

**Optimization**: Only poll when needed
```python
def update(self):
    # Only poll if session view is likely active
    if self.last_track_change_time > (time.time() - 0.5):
        self._poll_highlighted_clip_slot()
```

### 4. WebSocket Broadcast Optimization

**Current** (broadcasts to all clients):
```python
await server.websocket_server.broadcaster.broadcast(event_message)
```

**Optimized** (cursor on separate channel):
```python
# Option 1: Separate WebSocket endpoint
ws://localhost:8765/cursor

# Option 2: Message filtering on client
if (message.type === 'cursor_event') {
  cursorStore.update(message.payload);
}
```

## Svelte UI Integration

### Cursor Store (`cursor.svelte.ts`)

```typescript
interface CursorState {
  // Session View
  selectedTrackIdx: number | null;
  selectedSceneIdx: number | null;
  highlightedSlot: { track: number; scene: number } | null;
  
  // Arrangement View
  playheadPosition: number | null;  // beats
  
  // Detail View
  detailClipSlot: { track: number; scene: number } | null;
  selectedParameter: string | null;
}

let cursorState = $state<CursorState>({
  selectedTrackIdx: null,
  selectedSceneIdx: null,
  highlightedSlot: null,
  playheadPosition: null,
  detailClipSlot: null,
  selectedParameter: null
});

function applyCursorEvent(eventPath: string, args: any[]): void {
  switch (eventPath) {
    case '/live/cursor/track':
      cursorState.selectedTrackIdx = args[0];
      break;
    case '/live/cursor/scene':
      cursorState.selectedSceneIdx = args[0];
      break;
    case '/live/cursor/clip_slot':
      cursorState.highlightedSlot = {
        track: args[0],
        scene: args[1]
      };
      break;
    case '/live/cursor/playhead':
      cursorState.playheadPosition = args[0];
      break;
  }
}
```

### TreeNode Highlighting

```typescript
// In TreeNode component
let { node, depth, cursor }: { 
  node: ASTNode; 
  depth?: number;
  cursor?: CursorState;
} = $props();

// Check if this node is selected
let isSelected = $derived(
  node.node_type === 'track' && 
  node.attributes.index === cursor?.selectedTrackIdx
);

let isHighlighted = $derived(
  node.node_type === 'clip_slot' &&
  cursor?.highlightedSlot?.track === parentTrackIdx &&
  cursor?.highlightedSlot?.scene === sceneIdx
);
```

```svelte
<div 
  class="node-header" 
  class:selected={isSelected}
  class:highlighted={isHighlighted}
>
```

### CSS for Cursor Highlight

```css
.node-header.selected {
  background-color: rgba(59, 130, 246, 0.3);
  border-left: 3px solid #3b82f6;
}

.node-header.highlighted {
  background-color: rgba(251, 191, 36, 0.2);
  border-left: 3px solid #fbbf24;
}

/* Smooth transitions */
.node-header {
  transition: background-color 0.15s ease, border-left 0.15s ease;
}
```

## Performance Benchmarks

### Expected Latency (Session View)

| Step | Time | Cumulative |
|------|------|------------|
| User clicks track in Live | 0ms | 0ms |
| `selected_track` listener fires | ~1ms | 1ms |
| UDP message sent (localhost) | ~0.5ms | 1.5ms |
| UDP received & parsed | ~0.5ms | 2ms |
| WebSocket broadcast | ~2ms | 4ms |
| Browser receives message | ~2ms | 6ms |
| Cursor store updates | ~1ms | 7ms |
| Svelte re-renders TreeNode | ~5ms | 12ms |
| **Total latency** | | **~12ms** ✅ |

### Expected Latency (Arrangement View - Playhead)

| Step | Time | Cumulative |
|------|------|------------|
| Playhead moves (during playback) | 0ms | 0ms |
| `current_song_time` listener fires | ~1ms | 1ms |
| Throttle check (0.1 beat threshold) | ~0.1ms | 1.1ms |
| UDP message sent | ~0.5ms | 1.6ms |
| ... (same as above) | ~10ms | ~12ms |
| **Total latency** | | **~12ms** ✅ |

**Note**: Playhead updates at ~60 Hz max (every 16ms) due to throttling

## Testing Strategy

### Unit Tests

```python
# tests/test_cursor_observer.py
def test_session_cursor_sends_events():
    mock_sender = MockUDPSender()
    observer = SessionCursorObserver(mock_song, mock_sender)
    
    # Simulate track selection
    mock_song.view.selected_track = mock_song.tracks[5]
    observer._on_track_changed()
    
    assert mock_sender.last_event == ("/live/cursor/track", 5)
```

### Integration Tests

```python
# tests/test_cursor_latency.py
async def test_end_to_end_latency():
    # Start WebSocket server
    server = start_server()
    
    # Connect WebSocket client
    client = await connect_ws("ws://localhost:8765")
    
    # Send cursor event via UDP
    start_time = time.time()
    send_udp_cursor_event("/live/cursor/track", 0)
    
    # Wait for WebSocket message
    message = await client.recv()
    latency = (time.time() - start_time) * 1000  # ms
    
    assert latency < 20, f"Latency too high: {latency}ms"
```

### Manual Testing

1. **Session View**: Click different tracks → TreeView highlights instantly
2. **Clip Slot**: Click different clip slots → Highlights move smoothly
3. **Playback**: Press play → Playhead cursor moves in UI
4. **Detail View**: Open clip editor → Detail clip highlighted

## Implementation Order

### Sprint 1: Session View Cursor (Core)
1. ✅ Design architecture (this document)
2. ⏳ Implement `SessionCursorObserver` in Remote Script
3. ⏳ Add cursor event types to UDP listener
4. ⏳ Create `cursorStore` in Svelte
5. ⏳ Add highlight styles to TreeNode
6. ⏳ Test latency (<20ms)

### Sprint 2: Arrangement View Playhead
1. ⏳ Implement `ArrangementCursorObserver`
2. ⏳ Add playhead position to cursor store
3. ⏳ Add visual playhead indicator in UI
4. ⏳ Test with actual playback

### Sprint 3: Detail View Focus
1. ⏳ Implement `DetailCursorObserver`
2. ⏳ Track clip editor and device editor focus
3. ⏳ Add detail view indicators in UI

## Open Questions

### Q1: Should we track mouse hover in addition to selection?

**Answer**: No - too high frequency, not useful for TreeView

### Q2: Should playhead update continuously or snap to grid?

**Answer**: Throttle to 0.1 beat intervals (configurable)

### Q3: What if user has multiple windows (Session + Arrangement)?

**Answer**: Track both, let UI decide which to show

### Q4: Should we cache clip slot positions?

**Answer**: Yes - build cache on first access, invalidate on track add/remove

## Future Enhancements

### Smart Focus Following
- Auto-expand collapsed nodes when selected
- Auto-scroll to bring selected node into view
- Breadcrumb trail showing selection path

### Bi-directional Control
- Click node in TreeView → Select in Live
- Requires TCP command channel (already exists)
- Low priority (nice-to-have)

### Multi-Selection Support
- Live supports selecting multiple tracks (Shift+Click)
- Track as array of selected indices
- Highlight all selected nodes

## Conclusion

**Recommended Architecture**: Direct UDP → WebSocket path (no bridge)
- **Latency**: ~12ms (well under 20ms target)
- **Simplicity**: Reuses existing infrastructure
- **Reliability**: Proven with parameter updates

**Implementation Priority**:
1. Session View cursor (highest value, most used)
2. Arrangement View playhead (nice-to-have for playback)
3. Detail View focus (lowest priority)

**Next Step**: Implement `SessionCursorObserver` in Remote Script
