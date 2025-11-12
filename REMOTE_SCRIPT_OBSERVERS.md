# Remote Script Observer Pattern for Real-Time AST Updates

## Overview

We have **two sources** of AST changes that need to be synchronized:

1. **File-based changes** (User saves project → `.als` file changes)
   - Detected by: Hammerspoon `hs.pathwatcher`
   - Flow: `.als` → export XML → Python file watcher → diff → WebSocket broadcast
   - **Status**: ✅ Implemented

2. **Live API changes** (Real-time parameter/track/device changes)
   - Detected by: Remote Script observers
   - Flow: Live API event → Remote Script → ??? → WebSocket broadcast
   - **Status**: ⚠️ To be designed

## Challenge

**The Problem:**
- Remote Script runs inside Ableton Live (Python 3.11 in a sandboxed environment)
- WebSocket server runs as separate process (outside Ableton)
- They cannot directly communicate via Python imports/shared memory

**Current Communication:**
- Remote Script has TCP socket server on port 9001
- Hammerspoon sends commands via `nc` (netcat)
- Remote Script responds with JSON

## Proposed Solutions

### Option A: Remote Script as Event Publisher (Recommended)

**Architecture:**
```
┌──────────────────────────────────────┐
│     Ableton Live (Remote Script)     │
│  - Observes track/device/clip changes│
│  - Batches events (debouncing)       │
│  - Sends events to WebSocket server  │
└──────────┬───────────────────────────┘
           │ TCP Socket (bidirectional)
           │ {"type": "track_renamed", "track_id": ...}
           ▼
┌──────────────────────────────────────┐
│    Python WebSocket Server (8765)    │
│  - Receives Live API events          │
│  - Applies incremental changes       │
│  - Computes mini-diffs               │
│  - Broadcasts to web clients         │
└──────────┬───────────────────────────┘
           │ WebSocket
           ▼
┌──────────────────────────────────────┐
│       Svelte TreeViewer (5173)       │
│  - Applies diffs to tree             │
│  - Highlights changes                │
└──────────────────────────────────────┘
```

**Implementation Steps:**

1. **Add WebSocket client to Remote Script**
   ```python
   # In src/remote_script/ws_publisher.py
   class LiveEventPublisher:
       def __init__(self, ws_host="localhost", ws_port=8765):
           self.ws_url = f"ws://{ws_host}:{ws_port}"
           self.connection = None

       async def connect(self):
           # Connect to WebSocket server as a client
           self.connection = await websockets.connect(self.ws_url)

       async def publish_event(self, event_type, payload):
           # Send live event to server
           message = {
               "source": "remote_script",
               "type": event_type,
               "payload": payload
           }
           await self.connection.send(json.dumps(message))
   ```

2. **Add AST Change Observers**
   ```python
   # In src/remote_script/ast_observers.py
   class ASTChangeObservers:
       """Observes Live changes that affect AST structure"""

       def __init__(self, song, publisher):
           self.song = song
           self.publisher = publisher
           self._debounce_timers = {}

       def setup(self):
           # Track name changes
           for track in self.song.tracks:
               track.add_name_listener(
                   lambda track=track: self._on_track_renamed(track)
               )

           # Track additions/removals
           self.song.add_tracks_listener(self._on_tracks_changed)

           # Device additions/removals
           for track in self.song.tracks:
               track.devices_listener = self._on_devices_changed

           # More observers...
   ```

3. **Update WebSocket Server to Handle Remote Script Events**
   ```python
   # In src/websocket/server.py
   async def _handle_client(self, websocket):
       async for message_str in websocket:
           message = json.loads(message_str)

           if message.get("source") == "remote_script":
               # This is a Live API event
               await self._handle_live_event(message)
           else:
               # This is a web client message
               await self._handle_client_message(message, websocket)
   ```

**Pros:**
- Real-time updates (< 100ms latency)
- No need to re-parse XML for small changes
- Efficient - only transmits what changed
- Can update AST in-memory without file I/O

**Cons:**
- Requires Remote Script to connect to WebSocket as client
- More complex (bidirectional communication)
- Need to handle connection failures gracefully

### Option B: Hybrid Approach (File + Polling)

Keep file-based updates as primary, but add periodic polling for changes:

```python
# In Remote Script
def check_for_changes():
    # Compute lightweight hash of current state
    current_hash = compute_state_hash()
    if current_hash != last_hash:
        # Trigger XML export
        export_xml_command()
```

**Pros:**
- Simpler - reuses existing export mechanism
- No new communication channels needed
- Falls back to known-good file-based approach

**Cons:**
- Higher latency (1-5 seconds)
- More I/O overhead (constant XML exports)
- Still requires full diff computation

### Option C: Event Queue via File System

Remote Script writes events to a queue file, server reads them:

```
.vimabl/
  ├── project.xml
  └── events/
      ├── 001_track_renamed.json
      ├── 002_device_added.json
      └── ...
```

**Pros:**
- No network communication needed
- Natural persistence (events survive crashes)
- Simple to debug (just look at files)

**Cons:**
- High file I/O overhead
- Race conditions with file watching
- Cleanup complexity (when to delete old events?)

## Recommended Approach: Option A with Fallback

**Phase 1:** Implement file-based diff broadcasting (✅ Done)
**Phase 2:** Add Remote Script WebSocket client for real-time events
**Phase 3:** Hybrid - use real-time for small changes, file-based for saves

## Event Types to Observe

### High Priority (Structural Changes)
- `track_added` - New track created
- `track_removed` - Track deleted
- `track_renamed` - Track name changed
- `device_added` - New device on track
- `device_removed` - Device deleted
- `clip_added` - New clip in slot
- `clip_removed` - Clip deleted

### Medium Priority (Parameter Changes)
- `track_muted` - Mute state changed
- `track_armed` - Arm state changed
- `device_enabled` - Device on/off
- `parameter_changed` - Device parameter value

### Low Priority (Playback State)
- `clip_triggered` - Clip started playing
- `clip_stopped` - Clip stopped
- `transport_playing` - Play/stop state

## Debouncing Strategy

To avoid flooding the WebSocket with events:

```python
class EventDebouncer:
    def __init__(self, delay=0.5):  # 500ms debounce
        self.delay = delay
        self.pending_events = {}

    def debounce(self, event_key, event_data, callback):
        # Cancel existing timer for this event
        if event_key in self.pending_events:
            self.pending_events[event_key].cancel()

        # Schedule new timer
        timer = Timer(self.delay, lambda: callback(event_data))
        self.pending_events[event_key] = timer
        timer.start()
```

## Implementation Plan

1. ✅ **Phase 1: File-based diffs** (Completed)
   - XML file watching
   - Diff computation
   - WebSocket broadcasting

2. **Phase 2: Remote Script WebSocket client**
   - Add websockets library to Remote Script
   - Connect to server on startup
   - Send ping/pong for connection health

3. **Phase 3: Add AST observers**
   - Implement track/device/clip observers
   - Add debouncing
   - Send events to server

4. **Phase 4: Server-side event handling**
   - Receive remote script events
   - Apply incremental AST changes
   - Compute mini-diffs
   - Broadcast to clients

5. **Phase 5: Conflict resolution**
   - Handle case where file changes + live events conflict
   - Use timestamps to determine latest state
   - Re-sync on major conflicts (full reload)

## Notes

- Start simple: Only observe track name changes initially
- Test with large projects (50+ tracks)
- Measure performance impact on Ableton
- Consider user preference: "Enable real-time sync" toggle
- Document any Ableton performance impact
