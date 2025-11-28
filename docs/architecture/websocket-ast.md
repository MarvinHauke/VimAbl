# WebSocket AST Architecture

This document describes the architecture of VimAbl's WebSocket-based AST (Abstract Syntax Tree) visualization system, which provides real-time synchronization between Ableton Live and a web-based tree viewer.

## Overview

The WebSocket AST system enables live visualization of your Ableton Live project structure with sub-100ms latency. Changes made in Live are instantly reflected in the web UI through a combination of UDP event streaming and WebSocket broadcasting.

## System Architecture

```
┌─────────────────────┐
│   Ableton Live      │
│   Remote Script     │
└──────────┬──────────┘
           │ UDP (OSC)
           │ port 9002
           ↓
┌─────────────────────┐
│   UDP Listener      │
│   (Python)          │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐      ┌──────────────────┐
│   AST Server        │◄─────┤ XML File Watcher │
│   (Python)          │      │ (Watchdog)       │
└──────────┬──────────┘      └──────────────────┘
           │ WebSocket
           │ port 8765
           ↓
┌─────────────────────┐
│   Web UI            │
│   (Svelte 5)        │
└─────────────────────┘
```

## Core Components

### 1. UDP Listener (`src/udp_listener/listener.py`)

**Purpose**: Receives real-time OSC events from Ableton Live's Remote Script

**Architecture** (Phase 5j - Queue-Based):

```
UDP Socket (Port 9002)
    ↓
Receive Loop (non-blocking, async)
    ↓
Parse OSC Message
    ↓
Sequence Tracking (deduplication)
    ↓
Event Queue [put_nowait]
    ↓
┌─────────────────────────────┐
│  asyncio.Queue (1000 events)│
└─────────────────────────────┘
    ↓
Event Processor Task (concurrent)
    ↓
Event Callback (WebSocket broadcast)
```

**Key Features**:
- **Non-blocking reception**: UDP receives never block, even during slow WebSocket broadcasts
- **Event queue**: 1000-event asyncio.Queue decouples reception from processing
- **Concurrent tasks**: Receiver and processor run in parallel
- **Zero packet loss**: Tested with 55+ events in <1ms bursts
- **Sequence tracking**: Gap detection with monotonic sequence numbers
- **Statistics tracking**: Packets received, processed, dropped, queue depth

**Queue Benefits**:
- Prevents UDP buffer overflow during rapid event bursts (e.g., scene reordering)
- WebSocket broadcast latency doesn't affect UDP reception
- Graceful overload handling (queue fills → drop at source with logging)

**Message Format**:
```
/live/seq <seq_num:int> <timestamp:float> <event_path:string> <args...>
```

**Example**:
```
/live/seq 123 1234567890.123 /live/track/renamed 0 "My Track"
```

**Statistics Available**:
```python
stats = listener.get_stats()
# Returns:
{
    "packets_received": 1250,
    "packets_processed": 1250,
    "packets_dropped": 0,
    "parse_errors": 0,
    "queue_size": 3,
    "queue_max": 12,
    "sequence": {
        "total_received": 1250,
        "duplicates": 2,
        "gaps": 0,
        "gap_size_total": 0
    }
}
```

### 2. AST Server (`src/server/api.py`)

**Purpose**: Central server that manages the AST, processes events, and broadcasts updates.

**Core Class: `ASTServer`**
The main entry point that orchestrates AST management. It delegates specific functionality to specialized services and handlers.

*   **Services**:
    *   `QueryService`: Handles AST queries (`find_node_by_id`, `get_ast_json`, `diff_with_file`).
    *   `ProjectService`: Handles project loading and parsing (`load_project`).
*   **Event Routing**: Uses a registry (`_build_event_handler_registry`) to route OSC paths to specialized handlers.
*   **Debouncing**: Uses `DebouncedBroadcaster` for high-frequency events like parameters and tempo.

**Event Handlers (`src/server/handlers/`)**:
Logic for processing specific event types is refactored into dedicated classes:
*   `TrackEventHandler`: Handles track renaming and state changes (mute, arm, volume).
*   `DeviceEventHandler`: Handles device addition, deletion, and parameter updates.
*   `SceneEventHandler`: Handles scene operations (add, remove, rename, reorder).
*   `ClipSlotEventHandler`: Handles clip slot creation and status updates.
*   `TransportEventHandler`: Handles global transport state (play, tempo).

**AST Helpers (`src/server/ast_helpers.py`)**:
A suite of utility classes for AST manipulation and maintenance:
*   `ASTNavigator`: Static methods to find tracks, scenes, and traverse the tree.
*   `HashManager`: Recomputes node hashes and propagates changes up the tree.
*   `DiffGenerator`: Creates standardized diff objects (`added`, `removed`, `modified`, `state_changed`).
*   `SceneIndexManager`: Handles complex index shifting for scenes and clip slots during insertion/removal.
*   `ClipSlotManager`: Manages clip slot deduplication and ordered insertion by `scene_index`.
*   `ASTBuilder`: Bridges the gap between the raw XML parser and the `ASTNode` object structure.

**Event Handler Map**:

| Method | Event | Action |
|--------|-------|--------|
| `TrackEventHandler.handle_track_renamed` | `/live/track/renamed` | Update track name, rehash, broadcast diff |
| `TrackEventHandler.handle_track_state` | `/live/track/mute`<br>`/live/track/arm`<br>`/live/track/volume` | Update mixer attributes (no rehash) |
| `DeviceEventHandler.handle_device_added` | `/live/device/added` | Add device node, rehash, broadcast diff |
| `DeviceEventHandler.handle_device_deleted` | `/live/device/deleted` | Remove device node, rehash, broadcast diff |
| `SceneEventHandler.handle_scene_added` | `/live/scene/added` | Add scene, shift indices, broadcast diff |
| `SceneEventHandler.handle_scene_removed` | `/live/scene/removed` | Remove scene, shift indices, broadcast diff |
| `SceneEventHandler.handle_scene_renamed` | `/live/scene/renamed` | Update scene name, rehash, broadcast diff |
| `ClipSlotEventHandler.handle_clip_slot_created` | `/live/clip_slot/created` | Add/update clip slot, rehash, broadcast diff |

**Structural vs State Changes**:

- **Structural changes** (track rename, device add/delete, scene add/remove, clip slot creation):
  - Modify node structure or identity
  - Require hash recomputation
  - Broadcast as `DIFF_UPDATE` messages
  - Trigger visual indicators (green/yellow/red)

- **State changes** (mute, volume, parameters):
  - Lightweight attribute updates
  - No hash recomputation needed
  - Broadcast as `live_event` messages
  - Update silently (no visual indicator)

### 3. WebSocket Server (`src/server/websocket.py`)

**Purpose**: Manages WebSocket connections and message broadcasting

**Key Classes**:

#### `MessageBroadcaster`
Handles fan-out of messages to all connected clients:
- Maintains list of active connections
- Broadcasts to all clients simultaneously
- Handles connection errors gracefully
- Logs broadcast activity

#### `ASTWebSocketServer`
WebSocket server implementation:
- Starts asyncio server on specified host/port
- Handles client connections
- Sends full AST on connect
- Routes incoming messages (future: bi-directional control)
- Broadcasts diffs and live events

### 4. Serializers (`src/websocket/serializers.py`)

**Purpose**: Converts AST nodes and diffs into JSON-serializable formats for WebSocket communication, and constructs standardized WebSocket messages.

**Key Classes/Functions**:

#### `ASTSerializer`
Provides static methods for converting AST nodes and diff results into JSON-compatible dictionaries:
- `serialize_node(node: ASTNode, include_children: bool = True, depth: int = -1)`: Converts an AST node into a dictionary, optionally including children and controlling serialization depth.
- `serialize_diff(diff_result: Dict[str, Any])`: Converts a raw diff result dictionary into a standardized JSON-compatible diff representation, ensuring all change types are properly formatted.
- `to_json(data: Dict[str, Any], pretty: bool = False)`: A utility to convert any dictionary to a JSON string.

#### Message Creation Functions
Convenience functions for constructing specific WebSocket message types:
- `create_message(msg_type: str, payload: Dict[str, Any])`: General utility to create a message envelope.
- `create_full_ast_message(root: ASTNode, project_path: Optional[str] = None)`: Creates a `FULL_AST` message containing the entire serialized AST.
- `create_diff_message(diff_result: Dict[str, Any])`: Creates a `DIFF_UPDATE` message with serialized diff changes.
- `create_error_message(error: str, details: Optional[str] = None)`: Creates an `ERROR` message for broadcasting server-side issues.
- `create_ack_message(request_id: Optional[str] = None)`: Creates an `ACK` message to acknowledge client requests.

### 5. XML File Watcher (`src/main.py:XMLFileWatcher`)

**Purpose**: Detect when the user saves the project in Live and reload the AST

**Why Needed**:
- Structural changes (add/delete tracks) aren't fully supported via UDP
- UDP event gaps can cause desynchronization
- File save provides a reliable "checkpoint" for full sync

**How It Works**:
1. Uses `watchdog` library to monitor the XML file
2. Debounces events (1 second) to avoid duplicate reloads
3. On file change:
   - Load new XML and build fresh AST
   - Compare with old AST using `DiffVisitor`
   - Broadcast diff to all clients
4. If old AST exists, sends incremental diff
5. If first load, sends full AST

**Diff Format**:
```python
{
    'changes': [
        {
            'type': 'added',  # or 'removed', 'modified'
            'node_id': 'device_123',
            'node_type': 'device',
            'path': 'tracks[3].devices[1]',
            'new_value': {'name': 'Reverb', 'device_type': 'AudioEffect'}
        }
    ],
    'added': ['device_123'],
    'removed': ['device_456'],
    'modified': ['track_0']
}
```

### 5. Frontend AST Store (`src/web/frontend/src/lib/stores/ast.svelte.ts`)

**Purpose**: Manage AST state in the Svelte UI with Svelte 5 reactivity

**State Management**:
```typescript
interface ASTState {
  root: ASTNode | null;
  projectInfo: ProjectInfo | null;
  projectPath: string | null;
  lastSeqNum: number;
  isStale: boolean;
}

// Reactive state using Svelte 5 $state rune
let astState = $state<ASTState>({
  root: null,
  projectInfo: null,
  projectPath: null,
  lastSeqNum: 0,
  isStale: false
});
```

**Key Functions**:

#### `updateSequenceNumber(seqNum: number)`
Centralized sequence tracking for gap detection:
```typescript
function updateSequenceNumber(seqNum: number): void {
  if (astState.lastSeqNum > 0 && seqNum > astState.lastSeqNum + 1) {
    const gap = seqNum - astState.lastSeqNum - 1;
    console.warn(`Gap detected: ${gap} events missed`);
    astState.isStale = true;
  }
  astState.lastSeqNum = seqNum;
}
```

#### `applyDiff(diffPayload: any)`
Apply structured diff from XML file saves:
```typescript
function applyDiff(diffPayload: any): void {
  const changes = diffPayload.changes || diffPayload;

  for (const change of changes) {
    if (change.type === 'added') {
      // Create new node, mark as added, set 5s timer
      (newNode as any)._changeType = 'added';
      setTimeout(() => delete (newNode as any)._changeType, 5000);
    } else if (change.type === 'removed') {
      // Mark for removal, animate, delete after 500ms
      (node as any)._changeType = 'removed';
      setTimeout(() => { /* actually remove */ }, 500);
    } else if (change.type === 'modified') {
      // Update attributes, mark as modified
      (node as any)._changeType = 'modified';
      setTimeout(() => delete (node as any)._changeType, 5000);
    } else if (change.type === 'state_changed') {
      // Lightweight update, no visual indicator
    }
  }

  // Trigger Svelte 5 reactivity
  astState.root = astState.root;
}
```

#### `applyLiveEvent(eventPath: string, args: any[], seqNum: number)`
Apply real-time UDP events via AST Updater:
```typescript
function applyLiveEvent(eventPath: string, args: any[], seqNum: number): void {
  // Update sequence tracking
  if (seqNum > 0) {
    updateSequenceNumber(seqNum);
  }

  // Apply event to AST
  const success = astUpdater.updateFromLiveEvent(astState.root, eventPath, args);

  if (success) {
    // Throttle high-frequency events
    const isHighFrequency =
      eventPath === '/live/track/volume' ||
      eventPath === '/live/transport/tempo' ||
      eventPath === '/live/device/param';

    if (isHighFrequency) {
      // Only trigger reactivity every 100ms
      throttleTimer = window.setTimeout(() => {
        astState.root = astState.root;
      }, 100);
    } else {
      // Immediate update for structural changes
      astState.root = astState.root;
    }
  }
}
```

### 6. AST Node Types (`src/ast/node.py`)

**Purpose**: Defines the data model for the Ableton Live project's Abstract Syntax Tree (AST). Each node represents a distinct entity within the project (e.g., track, device, scene).

**Key Constructs**:

#### `NodeType` Enum
An enumeration defining all possible types of AST nodes. This provides a standardized way to identify node roles within the tree.
*   **Examples**: `PROJECT`, `TRACK`, `DEVICE`, `CLIP_SLOT`, `SCENE`, `MIXER`, `CLIP`, `FILE_REF`, `AUTOMATION`, `PARAMETER`.

#### `ASTNode` (Base Class)
The foundational class for all nodes in the AST. It provides common properties and methods for tree management:
*   `node_type`: The specific type of the node (from `NodeType` enum).
*   `id`: A unique identifier for the node (used for diffing and referencing).
*   `parent`: Reference to the parent node in the AST.
*   `children`: A list of child `ASTNode` objects.
*   `attributes`: A dictionary to store various properties specific to the node type (e.g., `name`, `index`, `volume`).
*   `hash`: A cryptographic hash representing the node's current state (used for efficient change detection).
*   `add_child(child)`: Adds a child node and sets its parent.
*   `remove_child(child)`: Removes a child node.

#### Concrete Node Types
Specialized `dataclass` implementations inheriting from `ASTNode`, each representing a specific Ableton Live entity:

*   **`ProjectNode`**: The root of the AST, representing the entire Ableton Live project. Key attributes: `version`, `creator`.
*   **`TrackNode`**: Represents an audio, MIDI, return, or master track. Key attributes: `name`, `index`, `color`, `is_muted`, `is_soloed`.
*   **`DeviceNode`**: Represents an instrument or effect device on a track. Key attributes: `name`, `device_type`, `is_enabled`.
*   **`ClipSlotNode`**: Represents a slot in the Session View grid where a clip can reside. Key attributes: `track_index`, `scene_index`, `has_clip`, `is_playing`, `is_triggered`.
*   **`ClipNode`**: Represents an actual MIDI or audio clip. Key attributes: `name`, `clip_type`, `start_time`, `end_time`, `is_looped`.
*   **`FileRefNode`**: Represents a reference to an external file (e.g., samples). Key attributes: `name`, `path`, `hash_val`, `ref_type`.
*   **`SceneNode`**: Represents a scene (horizontal row) in the Session View. Key attributes: `name`, `index`, `tempo`.
*   **`MixerNode`**: Represents the mixer section of a track. Key attributes: `volume`, `pan`, `is_muted`, `is_soloed`.
*   **`ParameterNode`**: Represents an automatable parameter of a device. Key attributes: `name`, `value`, `min`, `max`, `is_automated`.

### 7. AST Updater (`src/web/frontend/src/lib/stores/ast-updater.ts`)

**Purpose**: Map UDP events to AST node mutations

**Key Methods**:

```typescript
class ASTUpdater {
  updateFromLiveEvent(ast: ASTNode | null, eventPath: string, args: any[]): boolean {
    switch (eventPath) {
      case '/live/track/renamed':
        return this.updateTrackName(ast, args[0], args[1]);
      case '/live/track/mute':
        return this.updateTrackMute(ast, args[0], args[1]);
      case '/live/track/color':
        return this.updateTrackColor(ast, args[0], args[1]);
      case '/live/device/added':
        return this.addDevice(ast, args[0], args[1], args[2]);
      case '/live/device/deleted':
        return this.removeDevice(ast, args[0], args[1]);
      // ... more handlers
    }
  }

  private updateTrackName(ast: ASTNode, trackIndex: number, newName: string): boolean {
    const track = this.findTrack(ast, trackIndex);
    track.attributes.name = newName;

    // Mark as modified for visual indicator (yellow)
    (track as any)._changeType = 'modified';
    setTimeout(() => delete (track as any)._changeType, 5000);

    return true;
  }

  private addDevice(ast: ASTNode, trackIndex: number, deviceIndex: number, deviceName: string): boolean {
    const track = this.findTrack(ast, trackIndex);
    const newDevice: DeviceNode = { /* ... */ };
    track.children.splice(deviceIndex, 0, newDevice);

    // Mark as added for visual indicator (green)
    (newDevice as any)._changeType = 'added';
    setTimeout(() => delete (newDevice as any)._changeType, 5000);

    return true;
  }

  private removeDevice(ast: ASTNode, trackIndex: number, deviceIndex: number): boolean {
    const device = /* find device */;

    // Mark as removed for visual indicator (red)
    (device as any)._changeType = 'removed';

    // Remove after animation delay
    setTimeout(() => {
      track.children = track.children.filter(c => c.id !== device.id);
    }, 500);

    return true;
  }
}
```

**Visual Change Markers**:

The updater sets temporary `_changeType` markers on modified nodes:
- `'added'`: Green highlight with slide-in animation for 1 second
- `'modified'`: Yellow highlight with pulse animation for 1 second (suppressed if track is selected)
- `'removed'`: Red highlight with fade-out animation, then delete after 1 second

**Priority**: Blue selection highlighting takes precedence over yellow modification highlights to avoid visual confusion when editing the currently selected track.

### 7. TreeNode Component (`src/web/frontend/src/lib/components/TreeNode.svelte`)

**Purpose**: Recursive component that renders AST nodes with Svelte 5 reactivity

**Key Features**:

#### Svelte 5 Runes
```typescript
// Props using $props()
let { node, depth = 0 }: { node: ASTNode; depth?: number } = $props();

// Reactive state
let expanded = $state(depth < 2);
let isFlashing = $state(false);

// Derived values
let hasChildren = $derived(node.children && node.children.length > 0);
let changeType = $derived((node as any)._changeType || null);
let isSelectedTrack = $derived(
  node.node_type === 'track' &&
  cursorStore.selectedTrackIdx !== null &&
  node.attributes?.index === cursorStore.selectedTrackIdx
);

// Side effects
$effect(() => {
  if (isSelectedTrack && nodeHeaderElement) {
    nodeHeaderElement.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
  }
});
```

#### Flash Animation (First-Touch-Only)
```typescript
let previousAttributes = $state(JSON.stringify(node.attributes));
let hasFlashedForCurrentSequence = $state(false);
let changeTimer: number | null = null;

$effect(() => {
  const currentAttributes = JSON.stringify(node.attributes);
  if (previousAttributes !== currentAttributes) {
    // Flash only if we haven't flashed yet for this sequence
    if (!hasFlashedForCurrentSequence) {
      isFlashing = true;
      setTimeout(() => { isFlashing = false; }, 600);
      hasFlashedForCurrentSequence = true;
    }

    // Reset after 1 second of inactivity
    if (changeTimer !== null) clearTimeout(changeTimer);
    changeTimer = window.setTimeout(() => {
      hasFlashedForCurrentSequence = false;
    }, 1000);
  }
  previousAttributes = currentAttributes;
});
```

#### Visual Highlighting
```svelte
<div class="node-header"
     class:flashing={isFlashing}
     class:selected-track={isSelectedTrack}
     class:highlighted-slot={isHighlightedClipSlot}
     class:node-added={changeType === 'added'}
     class:node-modified={changeType === 'modified'}
     class:node-removed={changeType === 'removed'}
     style={trackColor ? `border-left: 4px solid ${trackColor}` : ''}>
  <!-- Node content -->
</div>
```

**CSS Animations**:
```css
/* Flash animation for attribute changes */
.node-header.flashing {
  animation: flash 0.6s ease-out;
}

@keyframes flash {
  0% { background-color: rgba(59, 130, 246, 0.4); transform: scale(1.02); }
  50% { background-color: rgba(59, 130, 246, 0.2); }
  100% { background-color: transparent; transform: scale(1); }
}

/* Color-coded change indicators */
.node-header.node-added {
  background-color: rgba(34, 197, 94, 0.15) !important;
  border-left: 3px solid #22c55e;  /* Green */
  animation: slideIn 0.5s ease-out;
}

.node-header.node-modified {
  background-color: rgba(251, 191, 36, 0.15) !important;
  border-left: 3px solid #fbbf24;  /* Yellow */
  animation: pulse 0.6s ease-out;
}

.node-header.node-removed {
  background-color: rgba(239, 68, 68, 0.15) !important;
  border-left: 3px solid #ef4444;  /* Red */
  text-decoration: line-through;
  opacity: 0.6;
  animation: fadeOut 0.5s ease-out;
}
```

## Data Flow Scenarios

### Scenario 1: User Renames Track in Live

```
1. User renames "Audio 1" → "Vocals" in Live
2. TrackObserver fires _on_name_changed()
3. Remote Script sends: /live/seq 123 <time> /live/track/renamed 0 "Vocals"
4. UDP Listener receives packet
5. Main.py udp_event_callback invoked
6. ASTServer.process_live_event() called
7. _handle_track_renamed() executes:
   - Finds track by index (0)
   - Updates track.attributes['name'] = "Vocals"
   - Recomputes hashes (track → project)
   - Generates diff: {type: 'modified', node_id: 'track_0', ...}
   - Broadcasts DIFF_UPDATE to WebSocket clients
8. Frontend receives DIFF_UPDATE message
9. astStore.applyDiff() called
10. Finds track node by ID
11. Updates attributes
12. Sets _changeType = 'modified' (5s timer)
13. Triggers reactivity: astState.root = astState.root
14. TreeView re-renders
15. TreeNode detects changeType = 'modified'
16. Yellow highlight + pulse animation for 5 seconds
```

**Latency**: ~50-100ms (UDP → visual update)

### Scenario 2: User Adds Device to Track

```
1. User drags "Reverb" onto track 0
2. DeviceObserver fires _on_device_added()
3. Remote Script sends: /live/seq 124 <time> /live/device/added 0 1 "Reverb"
4-7. [Same UDP → AST Server flow]
8. _handle_device_added() executes:
   - Finds track 0
   - Creates new DeviceNode
   - Inserts at index 1
   - Rehashes track → project
   - Broadcasts DIFF_UPDATE
9-11. [Same frontend flow]
12. astStore.applyDiff() creates new device node
13. Sets _changeType = 'added' (5s timer)
14. Triggers reactivity
15. TreeView re-renders with new device
16. Green highlight + slideIn animation for 5 seconds
```

### Scenario 3: User Saves Project (XML Reload)

```
1. User presses Cmd+S in Live
2. Live writes new XML file to disk
3. XMLFileWatcher detects file modification (watchdog)
4. Debounces for 1 second
5. _reload_and_broadcast() executes:
   - Stores old AST reference
   - Loads new XML with load_ableton_xml()
   - Builds new AST with build_ast()
   - Compares old vs new with DiffVisitor
   - Generates structured diff
   - Broadcasts DIFF_UPDATE
6-13. [Same frontend flow as Scenario 1]
```

**Use Cases**:
- User added/deleted tracks (not supported via UDP)
- UDP event gaps (> 5 events missed)
- Major structural changes

### Scenario 4: User Moves Volume Fader (High-Frequency)

```
1. User drags track 0 volume fader
2. MixerObserver fires _on_volume_changed() 10-20x/second
3. Remote Script sends: /live/seq 125-145 ... /live/track/volume 0 <value>
4-6. [UDP flow]
7. ASTServer.process_live_event():
   - Detects /live/device/param or /live/track/volume
   - Returns {broadcast_only: True} (no AST update)
8. Main.py broadcasts live_event message directly
9. Frontend receives live_event messages
10. astStore.updateSequenceNumber() for all events
11. If volume event: astStore.applyLiveEvent():
    - Detects high-frequency event
    - Sets pendingUpdate = true
    - Throttles to 100ms intervals
    - Only triggers reactivity every 100ms
12. TreeNode updates volume value
13. NO flash animation (silent update)
```

**Throttling Benefits**:
- Reduces re-renders from 200/sec to 10/sec
- Maintains 60 FPS
- Values still update smoothly

### Scenario 5: Gap Detection and Recovery

```
1. Network congestion causes UDP packet loss
2. Events 150-155 dropped (6 events)
3. Frontend receives event #156
4. astStore.updateSequenceNumber(156):
   - Detects gap: 156 - 149 - 1 = 6 events missed
   - Sets astState.isStale = true
   - Logs warning
5. ConnectionStatus component shows "⚠️ Stale"
6. User sees warning: "Save project to resync"
7. User presses Cmd+S in Live
8. XMLFileWatcher triggers full reload
9. Fresh AST sent via DIFF_UPDATE
10. Frontend receives and applies diff
11. astState.isStale = false
12. ConnectionStatus shows "🟢 Connected"
```

**Gap Threshold**: 5 events
**Recovery**: Manual save required

### Scenario 6: User Adds Scene (Server-Side AST Update)

```
1. User presses Cmd+I in Live (Insert Scene)
2. SceneObserver fires _on_scene_added()
3. Remote Script sends: /live/seq 160 <time> /live/scene/added 2 "Scene 3"
4. UDP Listener receives packet
5. ASTServer.process_live_event() called
6. _handle_scene_added() executes:
   - Uses SceneIndexManager to shift indices for all scenes > 2
   - Uses SceneIndexManager to shift scene_index for all clip slots > 2
   - Creates new SceneNode at index 2
   - Inserts SceneNode into AST children
   - Recomputes hashes
   - Generates complex diff (1 added scene, N modified scenes/slots)
   - Broadcasts DIFF_UPDATE
7. Frontend receives DIFF_UPDATE
8. astStore.applyDiff() executes:
   - Updates indices of existing nodes (no animation)
   - Inserts new scene node (Green highlight + slideIn)
9. TreeView re-renders with new scene structure
```

**Latency**: ~50-100ms
**Consistency**: Server AST remains authoritative source of truth

## Performance Optimizations

### 1. Throttling High-Frequency Events

**Problem**: Volume/parameter changes send 10-20 events/second, causing excessive re-renders

**Solution**:
```typescript
// Throttle to 100ms intervals
if (isHighFrequency) {
  pendingUpdate = true;
  if (throttleTimer === null) {
    throttleTimer = window.setTimeout(() => {
      if (pendingUpdate) {
        astState.root = astState.root;  // Trigger reactivity
        pendingUpdate = false;
      }
      throttleTimer = null;
    }, 100);
  }
}
```

**Impact**:
- Reduces re-renders by 90%
- Maintains smooth visual feedback
- Prevents UI jank

### 2. First-Touch-Only Flash Animation

**Problem**: Continuous parameter changes cause constant flashing (visually overwhelming)

**Solution**:
- First change: Flash immediately (shows *where* change is happening)
- Subsequent changes: Update values silently
- Reset after 1 second: Next change will flash again

**Benefits**:
- Clear visual indication of *location* without distraction
- Smooth value updates during continuous adjustments
- User-friendly for rapid parameter tweaking

### 3. Svelte 5 Fine-Grained Reactivity

**Advantage**: Only components with changed nodes re-render

**Mechanism**:
```typescript
// Svelte 5 tracks individual $state and $derived values
let hasChildren = $derived(node.children && node.children.length > 0);
let changeType = $derived((node as any)._changeType || null);

// When changeType changes, only this component re-renders
// Parent and sibling components are unaffected
```

**Impact**:
- Large projects (100+ tracks) maintain 60 FPS
- Minimal CPU usage
- Memory efficient

### 4. Selective Hash Recomputation

**Problem**: Recomputing entire tree is expensive

**Solution**:
- **Structural changes**: Rehash modified node + ancestors
- **State changes**: No rehashing (lightweight updates)

**Example**:
```python
# Track rename: rehash track → project
track_node.attributes['name'] = new_name
hash_tree(track_node)
self._recompute_parent_hashes(track_node)

# Track mute: no rehashing
mixer.attributes['is_muted'] = is_muted
# Broadcast state_changed event
```

### 5. Minimal Diff Broadcasting

**Problem**: Sending full AST on every change is wasteful

**Solution**: Send only changed nodes

```python
diff_result = {
    'changes': [{
        'type': 'modified',
        'node_id': track_node.node_id,
        'path': f"tracks[{track_idx}]",
        'old_value': {'name': old_name},
        'new_value': {'name': new_name}
    }],
    'modified': [track_node.node_id]
}
```

**Impact**:
- 100x smaller messages
- Lower network bandwidth
- Faster parsing

## Sequence Number Tracking

### Purpose
Detect when UDP events are dropped due to network issues

### Implementation

**Backend (src/main.py)**:
```python
last_seq_num = [0]
gap_threshold = 5

async def udp_event_callback(event_path, args, seq_num, timestamp):
    if last_seq_num[0] > 0:
        gap = seq_num - last_seq_num[0] - 1
        if gap > 0:
            print(f"[UDP] Gap detected: {gap} events")
            if gap >= gap_threshold:
                # Broadcast error, mark AST as stale
                await server.websocket_server.broadcast_error(
                    "UDP event gap detected",
                    f"Missed {gap} events. Save project to resync."
                )
    last_seq_num[0] = seq_num
```

**Frontend (ast.svelte.ts)**:
```typescript
function updateSequenceNumber(seqNum: number): void {
  if (astState.lastSeqNum > 0 && seqNum > astState.lastSeqNum + 1) {
    const gap = seqNum - astState.lastSeqNum - 1;
    console.warn(`Gap detected: ${gap} events missed`);
    astState.isStale = true;  // Triggers warning in UI
  }
  astState.lastSeqNum = seqNum;
}
```

### Centralized Tracking

**Problem**: Cursor events weren't updating sequence numbers, causing false gaps

**Solution**: Centralize tracking in +page.svelte before routing:

```typescript
else if (message.type === 'live_event') {
  // Update sequence for ALL events (cursor + AST)
  astStore.updateSequenceNumber(liveEvent.payload.seq_num);

  if (eventPath.startsWith('/live/cursor/')) {
    cursorStore.applyCursorEvent(eventPath, args);
  } else {
    astStore.applyLiveEvent(eventPath, args, 0);  // 0 = skip duplicate tracking
  }
}
```

## Error Handling

### UDP Packet Loss
- **Detection**: Sequence number gaps
- **Notification**: WebSocket ERROR message + stale flag
- **Recovery**: Save project → XML reload → full sync

### WebSocket Disconnection
- **Detection**: Connection status in frontend
- **Notification**: Red "Disconnected" indicator
- **Recovery**: Automatic reconnection attempts

### AST Parsing Errors
- **Detection**: Exception in load_ableton_xml()
- **Notification**: ERROR message to clients
- **Recovery**: Keep old AST, wait for next save

### Node Not Found
- **Detection**: find_track_by_index() returns None
- **Action**: Log warning, return early, no broadcast
- **Impact**: Event is skipped, no partial updates

## Future Enhancements

### Bi-Directional Control
Allow UI to send commands back to Live:

```typescript
// Frontend
function muteTrack(trackIndex: number) {
  websocket.send({
    type: 'command',
    payload: {
      command: 'mute_track',
      args: [trackIndex, true]
    }
  });
}

// Backend
if message['type'] == 'command':
    command = message['payload']['command']
    args = message['payload']['args']
    tcp_client.send_command(command, args)
```

### Structural Change Support
Implement full add/delete support without XML reload:

```python
async def _handle_track_added(self, args, seq_num):
    track_idx = args[0]
    track_name = args[1]

    # Create new TrackNode
    new_track = TrackNode(...)

    # Insert at correct index
    self.current_ast.children.insert(track_idx, new_track)

    # Update indices for subsequent tracks
    for i, track in enumerate(self.current_ast.children):
        if track.node_type == NodeType.TRACK:
            track.attributes['index'] = i

    # Rehash
    hash_tree(new_track)
    self._recompute_parent_hashes(new_track)

    # Broadcast
    await self.websocket_server.broadcast_diff({
        'changes': [{'type': 'added', ...}]
    })
```

### Smart Debouncing
Group rapid changes into batches:

```typescript
// Collect changes over 50ms window
let changeBuffer = [];
let debounceTimer = null;

function applyChange(change) {
  changeBuffer.push(change);

  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    applyBatchedChanges(changeBuffer);
    changeBuffer = [];
  }, 50);
}
```

## Related Documentation

- [Web Tree Viewer User Guide](../user-guide/web-treeviewer.md)
- [OSC Protocol Reference](../api-reference/osc-protocol.md)
- [UDP Observers](../user-guide/udp-observers.md)
- [Python Remote Script](python-remote-script.md)
