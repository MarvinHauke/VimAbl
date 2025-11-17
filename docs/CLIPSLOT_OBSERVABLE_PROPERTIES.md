# ClipSlot and Clip Observable Properties

**Date**: 2025-11-17
**Source**: Live API Documentation (Cycling '74)

## ClipSlot Properties - REAL-TIME OBSERVABLE ✅

These properties support `add_listener()` and fire callbacks when changed:

| Property | Type | Description | Event to Send |
|----------|------|-------------|---------------|
| `has_clip` | bool | Whether slot contains a clip | `/live/clip_slot/has_clip` |
| **`has_stop_button`** | bool | **Stop button enabled/disabled** | `/live/clip_slot/has_stop` |
| `playing_status` | int | Playback state (0=stopped, 1=playing, 2=triggered) | `/live/clip_slot/playing_status` |
| `is_triggered` | bool | Blinking trigger state | `/live/clip_slot/triggered` |
| `color` | int | Visual color value | `/live/clip_slot/color` |
| `color_index` | int | Color palette index | `/live/clip_slot/color_index` |
| `controls_other_clips` | bool | Stop other clips on launch | `/live/clip_slot/controls_others` |

### Key Discovery: `playing_status` is Better than `is_playing`!

**Use `playing_status` instead of separate listeners:**

```python
# BETTER APPROACH - Single listener for all playback states
def _on_playing_status_changed(self, scene_idx):
    """Called when clip_slot playback state changes."""
    clip_slot = self.track.clip_slots[scene_idx]
    status = clip_slot.playing_status

    # status values:
    # 0 = ClipSlot.STATUS_STOPPED
    # 1 = ClipSlot.STATUS_PLAYING
    # 2 = ClipSlot.STATUS_TRIGGERED (will play soon)

    self.sender.send_event("/live/clip_slot/playing_status",
                          self.track_index, scene_idx, status)
```

**Constants** (from Live API):
- `ClipSlot.STATUS_STOPPED = 0`
- `ClipSlot.STATUS_PLAYING = 1`
- `ClipSlot.STATUS_TRIGGERED = 2`

## Clip Properties - REAL-TIME OBSERVABLE ✅

If a clip exists in the slot, we can also observe these Clip properties:

### Playback State
| Property | Type | Description | Event to Send |
|----------|------|-------------|---------------|
| `is_playing` | bool | Currently playing | `/live/clip/is_playing` |
| `is_overdubbing` | bool | Recording overdubs | `/live/clip/is_overdubbing` |
| `muted` | bool | Clip is muted | `/live/clip/muted` |
| `looping` | bool | Loop enabled | `/live/clip/looping` |
| `playing_status` | int | Detailed playback state | `/live/clip/playing_status` |

### Clip Properties
| Property | Type | Description | Event to Send |
|----------|------|-------------|---------------|
| **`name`** | str | **Clip name** | `/live/clip/name` |
| `color` | int | Clip color | `/live/clip/color` |
| `gain` | float | Audio gain/volume | `/live/clip/gain` |
| `pitch_coarse` | int | Semitones transpose | `/live/clip/pitch_coarse` |
| `pitch_fine` | int | Cents transpose | `/live/clip/pitch_fine` |

### Loop/Timing Properties
| Property | Type | Description | Event to Send |
|----------|------|-------------|---------------|
| `start_marker` | float | Clip start position | `/live/clip/start_marker` |
| `end_marker` | float | Clip end position | `/live/clip/end_marker` |
| `loop_start` | float | Loop start position | `/live/clip/loop_start` |
| `loop_end` | float | Loop end position | `/live/clip/loop_end` |

### Launch Settings
| Property | Type | Description | Event to Send |
|----------|------|-------------|---------------|
| `launch_mode` | int | Launch behavior | `/live/clip/launch_mode` |
| `launch_quantization` | int | Launch timing | `/live/clip/launch_quantization` |
| `legato` | bool | Legato mode | `/live/clip/legato` |
| `velocity_amount` | float | Velocity sensitivity | `/live/clip/velocity_amount` |

### Audio-Specific Properties
| Property | Type | Description | Event to Send |
|----------|------|-------------|---------------|
| `warp_mode` | int | Warp algorithm | `/live/clip/warp_mode` |
| `warping` | bool | Warping enabled | `/live/clip/warping` |
| `groove` | Groove | Groove template | `/live/clip/groove` |

## Properties WITHOUT Listeners ❌

These can only be read, NOT observed:

### ClipSlot (Read-Only)
- `clip` - Reference to contained Clip object
- `is_group_slot` - Is this a group track slot
- `is_playing` - Derived from playing_status (use playing_status listener instead)
- `is_recording` - Derived from playing_status

### Clip (Read-Only)
- `file_path` - Audio file path
- `length` - Clip duration
- `playing_position` - Current playhead position
- `is_midi_clip` / `is_audio_clip` - Clip type
- `is_arrangement_clip` - Location type
- `sample_length` - Audio sample length
- Many others (see full API docs)

## Implementation Strategy

### Phase 6e: Real-Time ClipSlot Observers (Updated)

Based on available listeners, we should observe:

1. **ClipSlot level** (always observable):
   - ✅ `has_clip` - Detect clip add/remove
   - ✅ `has_stop_button` - **Detect stop button changes in real-time!**
   - ✅ `playing_status` - Single listener for playing/triggered/stopped
   - ✅ `color` - Detect color changes
   - ❌ ~~`is_playing`~~ - Use `playing_status` instead
   - ❌ ~~`is_triggered`~~ - Use `playing_status` instead

2. **Clip level** (when has_clip=True):
   - ✅ `name` - Detect clip renames
   - ✅ `color` - Detect clip color changes
   - ✅ `muted` - Detect clip mute state
   - ✅ `looping` - Detect loop toggle
   - ✅ Other properties as needed (gain, pitch, etc.)

### Recommended Observer Setup

```python
class TrackObserver:
    def _observe_clip_slots(self):
        """Set up listeners for all clip slots on this track."""
        for scene_idx, clip_slot in enumerate(self.track.clip_slots):
            # Store initial state
            self.clip_slot_states[(self.track_index, scene_idx)] = {
                'has_clip': clip_slot.has_clip,
                'has_stop_button': clip_slot.has_stop_button,
                'playing_status': clip_slot.playing_status,
                'color': clip_slot.color,
            }

            # Create callbacks
            callbacks = {
                'has_clip': self._create_has_clip_callback(scene_idx),
                'has_stop_button': self._create_has_stop_callback(scene_idx),
                'playing_status': self._create_playing_status_callback(scene_idx),
                'color': self._create_slot_color_callback(scene_idx),
            }
            self.clip_slot_callbacks[scene_idx] = callbacks

            # Add ClipSlot listeners
            clip_slot.add_has_clip_listener(callbacks['has_clip'])
            clip_slot.add_has_stop_button_listener(callbacks['has_stop_button'])
            clip_slot.add_playing_status_listener(callbacks['playing_status'])
            clip_slot.add_color_listener(callbacks['color'])

            # If slot has a clip, observe Clip properties
            if clip_slot.has_clip:
                self._observe_clip(clip_slot.clip, scene_idx)

    def _observe_clip(self, clip, scene_idx):
        """Observe properties of a Clip object."""
        clip_callbacks = {
            'name': lambda: self._on_clip_name_changed(scene_idx),
            'color': lambda: self._on_clip_color_changed(scene_idx),
            'muted': lambda: self._on_clip_muted_changed(scene_idx),
            'looping': lambda: self._on_clip_looping_changed(scene_idx),
        }

        # Store callbacks for cleanup
        self.clip_callbacks[scene_idx] = clip_callbacks

        # Add Clip listeners
        clip.add_name_listener(clip_callbacks['name'])
        clip.add_color_listener(clip_callbacks['color'])
        clip.add_muted_listener(clip_callbacks['muted'])
        clip.add_looping_listener(clip_callbacks['looping'])

    def _on_clip_name_changed(self, scene_idx):
        """Called when clip name changes."""
        clip_slot = self.track.clip_slots[scene_idx]
        if clip_slot.has_clip:
            name = clip_slot.clip.name
            self.sender.send_event("/live/clip/name",
                                  self.track_index, scene_idx, name)
            self.log(f"Clip [{self.track_index},{scene_idx}] renamed: '{name}'")
```

## OSC Event Schema (Updated)

### ClipSlot Events

```python
# Has clip changed (clip added/removed)
/live/clip_slot/has_clip <track_idx> <scene_idx> <has_clip_bool>

# Stop button changed (user enabled/disabled stop button)
/live/clip_slot/has_stop <track_idx> <scene_idx> <has_stop_bool>

# Playing status changed (0=stopped, 1=playing, 2=triggered)
/live/clip_slot/playing_status <track_idx> <scene_idx> <status_int>

# Slot color changed
/live/clip_slot/color <track_idx> <scene_idx> <color_int>
```

### Clip Events (when has_clip=True)

```python
# Clip name changed
/live/clip/name <track_idx> <scene_idx> <name_str>

# Clip color changed
/live/clip/color <track_idx> <scene_idx> <color_int>

# Clip muted
/live/clip/muted <track_idx> <scene_idx> <muted_bool>

# Clip looping changed
/live/clip/looping <track_idx> <scene_idx> <looping_bool>
```

## Web UI State Management

### ClipSlot Attributes (in AST)

```typescript
interface ClipSlotAttributes {
    track_index: number;
    scene_index: number;

    // From XML (initial state)
    has_clip: boolean;
    has_stop_button: boolean;  // Can change in real-time!

    // From real-time events
    playing_status: number;  // 0=stopped, 1=playing, 2=triggered
    color: number;

    // Derived for convenience
    is_playing: boolean;     // playing_status === 1
    is_triggered: boolean;   // playing_status === 2
}

interface ClipAttributes {
    name: string;
    clip_type: 'midi' | 'audio';

    // Real-time state
    is_playing: boolean;
    muted: boolean;
    looping: boolean;
    color: number;

    // From XML (relatively static)
    start_time: number;
    end_time: number;
    loop_start: number;
    loop_end: number;
    // ... etc
}
```

### AST Updater Events

```typescript
export function updateFromLiveEvent(ast: ASTNode, eventPath: string, args: any[]): boolean {
    switch (eventPath) {
        case '/live/clip_slot/has_stop': {
            const [trackIdx, sceneIdx, hasStop] = args;
            const clipSlot = findClipSlot(ast, trackIdx, sceneIdx);
            if (clipSlot) {
                clipSlot.attributes.has_stop_button = hasStop !== 0;
                return true;
            }
            return false;
        }

        case '/live/clip_slot/playing_status': {
            const [trackIdx, sceneIdx, status] = args;
            const clipSlot = findClipSlot(ast, trackIdx, sceneIdx);
            if (clipSlot) {
                clipSlot.attributes.playing_status = status;
                // Update derived properties
                clipSlot.attributes.is_playing = (status === 1);
                clipSlot.attributes.is_triggered = (status === 2);
                return true;
            }
            return false;
        }

        case '/live/clip/name': {
            const [trackIdx, sceneIdx, name] = args;
            const clipSlot = findClipSlot(ast, trackIdx, sceneIdx);
            if (clipSlot && clipSlot.attributes.has_clip) {
                // Find ClipNode child
                const clipNode = clipSlot.children.find(c => c.node_type === 'clip');
                if (clipNode) {
                    clipNode.attributes.name = name;
                    return true;
                }
            }
            return false;
        }

        case '/live/clip/muted': {
            const [trackIdx, sceneIdx, muted] = args;
            const clipSlot = findClipSlot(ast, trackIdx, sceneIdx);
            if (clipSlot && clipSlot.attributes.has_clip) {
                const clipNode = clipSlot.children.find(c => c.node_type === 'clip');
                if (clipNode) {
                    clipNode.attributes.muted = muted !== 0;
                    return true;
                }
            }
            return false;
        }

        // ... other clip properties ...
    }
}
```

## Performance Considerations

### Number of Listeners

For a project with:
- 32 tracks
- 8 scenes
- 50% slots filled with clips

**ClipSlot listeners**: 32 × 8 × 4 properties = **1,024 listeners**
**Clip listeners**: 32 × 8 × 0.5 × 4 properties = **512 listeners**
**Total**: ~**1,536 listeners**

This is ACCEPTABLE - Push 2 controller has thousands of listeners and works fine.

### Debouncing

Properties that might fire rapidly:
- `playing_status` - Should NOT debounce (state changes are discrete)
- `color` - Can debounce (50ms)
- `clip.name` - No debounce needed (infrequent)

## Summary

**YES, we can observe almost everything in real-time!** ✅

The key properties you asked about:
- ✅ **Stop button deletion**: `has_stop_button` listener
- ✅ **Clip playing/deactivated**: `playing_status` listener (better than `is_playing`)
- ✅ **Clip name changes**: `clip.name` listener
- ✅ **Clip add/remove**: `has_clip` listener (already implemented)

The only limitation is we must add **individual listeners** for each property - there's no "observe all" listener. But that's fine, we just add them all in our `_observe_clip_slots()` method.
