# VimAbl Svelte TreeViewer Implementation TODO

## Overview

This document outlines the implementation plan for adding a **Svelte-based Web TreeViewer** to VimAbl. The feature will provide a real-time visual representation of an Ableton Live Set's internal structure (AST), powered by Python, WebSockets, and Svelte.

**Reference Document**: `SVELTE_TREEVIEWER.md`

---

## Current State Analysis

Your AST architecture is solid with:

- ✅ Well-structured node classes (ProjectNode, TrackNode, DeviceNode, ClipNode, etc.)
- ✅ Visitor pattern implementation (serialization, diffing, searching)
- ✅ Incremental hashing for change detection
- ✅ Server API with query/diff operations
- ✅ Phase 1a-1b complete: Devices, Clips, Scenes, Mixer parsing
- ✅ Remote Script with XML export capability
- ✅ Socket server on port 9001 (Live API commands)

**What's Missing**: Real-time web visualization with WebSocket streaming and Svelte frontend.

---

## Architecture Vision

### System Architecture

```
┌────────────────────────────────────────┐
│           Ableton Live Set             │
│  (.als XML / Live API + Remote Script) │
└────────────────┬───────────────────────┘
                 │
                 ▼
    ┌──────────────────────────┐
    │  Python AST Layer         │
    │  - Parses XML → JSON AST  │
    │  - Watches Live changes   │
    │  - Computes SHAs / Diffs  │
    └──────────┬───────────────┘
               │
   (WebSocket JSON stream - Port 8765)
               │
               ▼
┌────────────────────────────────┐
│  Svelte Frontend (Local Web UI)│
│  - Renders AST interactively   │
│  - Highlights live updates     │
│  - Displays diffs + file refs  │
└────────────────────────────────┘
```

### Port Allocation

- **Port 9001**: Remote Script (existing - Live API commands)
- **Port 8765**: WebSocket Server (new - AST streaming)
- **Port 5173**: Svelte Dev Server (development)

---

## Phase 1: WebSocket Server Foundation ✅ COMPLETE

**Priority: HIGH**
**Dependencies: Existing AST parser (Phase 1a-1b from previous TODO)**
**Goal: Create WebSocket server that can stream AST updates**

### Implementation Status

The WebSocket server and Hammerspoon integration are complete! Key components:

**Hammerspoon Integration:**

- `src/hammerspoon/websocket_manager.lua` - Manages WebSocket server process lifecycle
- `src/hammerspoon/keys/websocket.lua` - Keybindings for manual control
- `src/hammerspoon/app_watcher.lua` - Auto-starts server when Ableton launches
- `src/remote_script/commands.py` - Added `GET_PROJECT_PATH` command

**How It Works:**

1. Ableton Live launches → Hammerspoon detects it
2. Waits 5 seconds for Live to fully load
3. Queries Remote Script for current project path
4. Starts WebSocket server using `uv run python -m src.main`
5. Server streams AST updates on port 8765
6. When Ableton quits → Server stops automatically

**Manual Controls:**

- `Cmd+Shift+W` - Toggle WebSocket server
- `Cmd+Shift+R` - Restart server
- `Cmd+Shift+I` - Show server status

### Phase 1a: WebSocket Server Setup ✅ COMPLETE

- [x] Create `src/websocket/` directory structure
  - [x] Create `src/websocket/__init__.py`
  - [x] Create `src/websocket/server.py` - Main WebSocket server class
  - [x] Create `src/websocket/broadcaster.py` - Message broadcasting utility
  - [x] Create `src/websocket/handlers.py` - WebSocket event handlers
- [x] Implement `ASTWebSocketServer` class in `server.py`
  - [x] Use `websockets` library (add to requirements.txt)
  - [x] Listen on port 8765
  - [x] Maintain connected clients list
  - [x] Handle client connections/disconnections
  - [x] Implement graceful shutdown
- [x] Implement basic message protocol
  - [x] Define message types (FULL_AST, DIFF_UPDATE, ERROR, ACK)
  - [x] Create JSON serialization for AST nodes
  - [x] Add message validation
- [x] Add error handling and logging
  - [x] Connection errors
  - [x] JSON serialization errors
  - [x] Client disconnection handling
- [x] Test WebSocket server
  - [x] Start server standalone
  - [x] Connect with test client (websocat or Python script)
  - [x] Send test AST data
  - [x] Verify JSON format is correct

### Phase 1b: Integration with Existing AST System ✅ COMPLETE

- [x] Update `src/server/api.py` - Integrate WebSocket broadcasting
  - [x] Add WebSocket server instance to `ASTServer`
  - [x] Broadcast full AST on initial client connection
  - [x] Broadcast diffs when AST changes
  - [x] Handle multiple connected clients
- [x] Implement AST change detection
  - [x] Use existing `DiffVisitor` to compute changes
  - [x] Trigger broadcast on file watch events (via load_project)
  - [x] Async task creation for broadcasting
- [x] Create `src/websocket/serializers.py` - AST to JSON converters
  - [x] Convert AST nodes to JSON-serializable dicts
  - [x] Preserve node IDs, types, attributes
  - [x] Include hash information
  - [x] Optimize payload size (supports depth parameter)
- [x] Test integration
  - [x] Start AST server with WebSocket enabled (via uv run python -m src.main)
  - [x] Parse example project
  - [x] Connect WebSocket client
  - [x] Verify full AST is received
  - [x] Auto-start via Hammerspoon working

### Phase 1c: Command-Line Interface Updates ✅ COMPLETE

- [x] Update `src/main.py` - Add WebSocket mode
  - [x] Add `--mode=websocket` option
  - [x] Add `--ws-port` argument (default 8765)
  - [x] Start WebSocket server alongside AST server
  - [x] Enable file watching by default in WebSocket mode
- [x] Add startup scripts
  - [x] Hammerspoon integration for auto-start (websocket_manager.lua)
  - [x] App watcher for automatic server startup (app_watcher.lua)
  - [x] Manual controls via keybindings (Cmd+Shift+W)
- [x] Test CLI
  - [x] Run: `python3 -m src.main Example_Project/example.als --mode=websocket`
  - [x] Verify server starts on port 8765
  - [x] Check logs for connection status

---

## Phase 2: Svelte Frontend Foundation

**Priority: HIGH**
**Dependencies: Phase 1a (WebSocket server)**
**Goal: Create basic Svelte app that can display AST**

### Phase 2a: SvelteKit Project Setup ✅ COMPLETE

- [x] Create `src/web/frontend/` directory
- [x] Initialize SvelteKit project
  - [x] Run: `npm create svelte@latest src/web/frontend`
  - [x] Choose: Skeleton project, TypeScript
  - [x] Install dependencies: `npm install`
- [x] Configure Tailwind CSS
  - [x] Install: `npm install -D tailwindcss postcss autoprefixer`
  - [x] Configured with Tailwind v4
  - [x] Tailwind working in components
- [x] Set up project structure
  - [x] Create `src/lib/components/` - Svelte components
  - [x] Create `src/lib/stores/` - Svelte stores
  - [x] Create `src/lib/api/` - WebSocket client
  - [x] Create `src/lib/types/` - TypeScript types
- [x] Configure dev server
  - [x] Update `vite.config.ts` for port 5173
  - [x] HMR configured
- [x] Test setup
  - [x] Run: `npm run dev`
  - [x] Open `http://localhost:5173`
  - [x] Verify default page loads

### Phase 2b: WebSocket Client Implementation ✅ COMPLETE

- [x] Create `src/lib/api/websocket.ts` - WebSocket client
  - [x] Implement connection to `ws://localhost:8765`
  - [x] Handle connection lifecycle (open, close, error)
  - [x] Parse incoming JSON messages
  - [x] Implement reconnection logic (exponential backoff)
  - [x] Add TypeScript types for messages
- [x] Create `src/lib/stores/ast.ts` - AST state management
  - [x] Use Svelte writable store for AST data
  - [x] Store full AST tree
  - [x] Handle FULL_AST messages (replace entire tree)
  - [ ] Handle DIFF_UPDATE messages (patch existing tree) - TODO Phase 3
  - [ ] Add derived stores for statistics (track count, etc.) - TODO Phase 4c
- [x] Create `src/lib/stores/connection.ts` - Connection state
  - [x] Track WebSocket connection status
  - [x] Store error messages
  - [x] Track last update timestamp
- [x] Create `src/lib/types/ast.ts` - TypeScript AST types
  - [x] Define interfaces for all node types
  - [x] Match Python node structure
  - [x] Message types defined
- [x] Test WebSocket client
  - [x] Start WebSocket server
  - [x] Start Svelte dev server
  - [x] Verify connection in browser console (logs show "Connected" and "FULL_AST" received)
  - [x] Check that AST data is received and stored (1074 nodes loaded successfully)

### Phase 2c: Basic Tree Component ✅ COMPLETE

- [x] Create `src/lib/components/TreeNode.svelte` - Recursive tree node
  - [x] Display node type and name
  - [x] Show/hide children (collapsible)
  - [x] Display node attributes (node_id, name)
  - [x] Recursive rendering of child nodes
  - [x] Add expand/collapse icons (▶/▼)
  - [x] Auto-expand first 2 levels
- [x] Create `src/lib/components/TreeView.svelte` - Root tree container
  - [x] Render top-level tree structure
  - [x] Handle empty state (no AST loaded)
  - [x] Show project metadata (total nodes, max depth, project path)
  - [x] Display statistics (node count, tree depth)
  - [ ] Add search/filter input (basic) - **DEFERRED to Phase 4a**
- [x] Create `src/lib/components/ConnectionStatus.svelte` - Status indicator
  - [x] Show connection state (connected, disconnected, error)
  - [x] Display last update time
  - [x] Show error messages if any
- [x] Create main page `src/routes/+page.svelte`
  - [x] Import and use ConnectionStatus component
  - [x] Import and use TreeView component
  - [x] Add basic layout (header, main content)
  - [x] Style with Tailwind CSS
  - [x] Unsaved project warning (yellow banner)
- [x] Test basic rendering
  - [x] Load example project in WebSocket server
  - [x] Open Svelte app in browser
  - [x] Verify connection and AST data displays (482 nodes tested)
  - [x] Test expand/collapse functionality (working)

---

## Phase 3: Real-Time Updates & Diff Visualization

**Priority: HIGH**
**Dependencies: Phase 1b, Phase 2c**
**Goal: Highlight changes in real-time when AST updates**

### Phase 3a: Diff Application Logic

- [ ] Enhance `src/lib/stores/ast.ts` - Add diff patching
  - [ ] Implement `applyDiff(diff)` function
  - [ ] Handle node additions (new tracks, devices, clips)
  - [ ] Handle node deletions (removed items)
  - [ ] Handle node modifications (changed attributes)
  - [ ] Preserve expand/collapse state during updates
- [ ] Create `src/lib/utils/diff.ts` - Diff utilities
  - [ ] Parse diff format from Python server
  - [ ] Map diff paths to tree nodes
  - [ ] Compute which nodes changed
  - [ ] Add TypeScript types for diffs
- [ ] Add change tracking to tree store
  - [ ] Mark nodes as added/modified/removed
  - [ ] Store timestamp of last change per node
  - [ ] Auto-clear change markers after timeout (5s)
- [ ] Test diff application
  - [ ] Modify .als file while app is open
  - [ ] Verify diff is received via WebSocket
  - [ ] Check that tree updates correctly
  - [ ] Ensure expand/collapse state persists

### Phase 3b: Visual Diff Indicators

- [ ] Update `TreeNode.svelte` - Add change highlighting
  - [ ] Add CSS classes for change types
    - [ ] `.node-added` - Green background for new nodes
    - [ ] `.node-modified` - Yellow background for changed nodes
    - [ ] `.node-removed` - Red background, strikethrough for removed nodes
  - [ ] Fade out highlights after 5 seconds
  - [ ] Add smooth transitions (CSS animations)
- [ ] Create `src/lib/components/DiffLegend.svelte` - Change type legend
  - [ ] Show color coding explanation
  - [ ] Display recent change count
  - [ ] Add "clear highlights" button
- [ ] Add animation effects
  - [ ] Slide-in animation for new nodes
  - [ ] Pulse effect for modified nodes
  - [ ] Fade-out for removed nodes
- [ ] Test visual feedback
  - [ ] Add a track in Ableton
  - [ ] Verify green highlight appears
  - [ ] Rename a track
  - [ ] Verify yellow highlight appears
  - [ ] Delete a track
  - [ ] Verify red highlight and strikethrough

### Phase 3c: Performance Optimization

- [ ] Implement virtual scrolling for large trees
  - [ ] Use library like `svelte-virtual-list`
  - [ ] Render only visible nodes
  - [ ] Add scroll position restoration
- [ ] Optimize re-rendering
  - [ ] Add `key` bindings for list items
  - [ ] Use `{#key}` blocks strategically
  - [ ] Memoize expensive computations
- [ ] Add debouncing for rapid updates
  - [ ] Batch multiple diffs into single update
  - [ ] Prevent UI flickering
- [ ] Test with large project
  - [ ] Load project with 50+ tracks
  - [ ] Verify smooth scrolling
  - [ ] Check memory usage
  - [ ] Test rapid changes (automation recording)

---

## Phase 4: Enhanced UI Features

**Priority: MEDIUM**
**Dependencies: Phase 3**
**Goal: Add search, filtering, and navigation features**

### Phase 4a: Search & Filter

- [ ] Create `src/lib/components/SearchBar.svelte` - Search input
  - [ ] Text input with debouncing
  - [ ] Search by node name
  - [ ] Search by node type (track, device, clip)
  - [ ] Highlight matching nodes
  - [ ] Show match count
- [ ] Implement search logic in `src/lib/stores/search.ts`
  - [ ] Full-text search across all nodes
  - [ ] Filter by node type
  - [ ] Filter by attributes (muted, armed, etc.)
  - [ ] Support regex patterns
- [ ] Add search results navigation
  - [ ] "Next match" button (keyboard: n)
  - [ ] "Previous match" button (keyboard: N)
  - [ ] Auto-expand tree to show matches
  - [ ] Scroll to matching nodes
- [ ] Test search functionality
  - [ ] Search for device name
  - [ ] Search for track name
  - [ ] Filter by node type
  - [ ] Verify matches highlight correctly

### Phase 4b: Node Details Panel

- [ ] Create `src/lib/components/NodeDetails.svelte` - Details view
  - [ ] Show selected node's full attributes
  - [ ] Display node hash (SHA)
  - [ ] Show file references (for devices/clips)
  - [ ] Display parent/child relationships
  - [ ] Add "Copy JSON" button
- [ ] Add node selection to tree
  - [ ] Click node to select
  - [ ] Highlight selected node
  - [ ] Store selected node ID in store
  - [ ] Keyboard navigation (arrow keys)
- [ ] Create split-pane layout
  - [ ] Tree on left (60% width)
  - [ ] Details on right (40% width)
  - [ ] Resizable divider
- [ ] Test details panel
  - [ ] Click on various nodes
  - [ ] Verify attributes display correctly
  - [ ] Test "Copy JSON" functionality

### Phase 4c: Project Statistics Dashboard

- [ ] Create `src/lib/components/ProjectStats.svelte` - Stats widget
  - [ ] Display total track count
  - [ ] Display total device count
  - [ ] Display total clip count
  - [ ] Display file reference count
  - [ ] Show project name and path
  - [ ] Display last modified timestamp
- [ ] Add statistics computation
  - [ ] Create derived stores for counts
  - [ ] Update in real-time as AST changes
  - [ ] Show diff compared to previous state
- [ ] Create `src/lib/components/FileReferences.svelte` - File list
  - [ ] List all audio/sample files
  - [ ] Show file paths
  - [ ] Display file hashes
  - [ ] Highlight missing files (if detectable)
  - [ ] Add "Copy path" buttons
- [ ] Test dashboard
  - [ ] Load project and verify counts
  - [ ] Make changes, verify counts update
  - [ ] Check file reference list

---

## Phase 5: Remote Script Integration (UDP/OSC Real-Time Observer)

**Priority: HIGH** (Changed from MEDIUM - critical for real-time updates)
**Dependencies: Phase 1, Phase 3**
**Goal: Stream real-time updates from Ableton Live via UDP/OSC protocol**

### Architecture Overview

```
                     (A) .als file watcher
          ┌────────────────────────────────┐
          │  Python AST Server (Port 8765) │
          │  - Maintains AST               │
          │  - Computes diffs              │
          │  - WebSocket broadcast to UI   │
          └──────────┬─────────────────────┘
                     ▲
   (D) UDP/OSC ⇡     │  ⇣ WebSocket (to Svelte)
      Port 9002      │
                     ▼
          ┌────────────────────────────────┐
          │  UDP Listener Bridge           │
          │  - Receives OSC events         │
          │  - Deduplicates messages       │
          │  - Forwards to AST server      │
          └──────────┬─────────────────────┘
                     ▲
   UDP (fire & forget, < 1ms latency)
                     │
          ┌──────────┴─────────────────────┐
          │  Ableton Remote Script         │
          │  - Live API observers          │
          │  - Emits OSC/UDP events        │
          │  - Debounces rapid changes     │
          └────────────────────────────────┘
```

**Port Allocation:**

- **9001**: Remote Script TCP server (existing - commands)
- **9002**: UDP listener (new - real-time events)
- **8765**: WebSocket server (existing - AST to Svelte)

**Why UDP/OSC?**

- ✅ Very low latency (< 1 ms) - no blocking inside Live
- ✅ Fire-and-forget - Remote Script never waits
- ✅ Ableton-friendly pattern (same as Max for Live, TouchOSC)
- ✅ Easy to debug with OSC monitoring tools
- ✅ Lightweight - just `socket.sendto()` in Python
- ⚠️ UDP is unreliable - use XML diff as fallback for guaranteed consistency

**Future Option: ZeroMQ (deferred to Phase 9)**

- For production/distributed setups
- PUB/SUB pattern with auto-reconnect
- Requires `pyzmq` packaging in Remote Script
- Overkill for current local-only use case

### Phase 5a: UDP/OSC Message Schema Design ✅ COMPLETE

**Goal: Define lightweight, OSC-compatible message format**

- [x] Design OSC message schema (in `docs/OSC_PROTOCOL.md`)
  - [x] Track events:
    - `/live/track/renamed <track_idx> <name>`
    - `/live/track/added <track_idx> <name> <type>`
    - `/live/track/deleted <track_idx>`
    - `/live/track/mute <track_idx> <muted_bool>`
    - `/live/track/arm <track_idx> <armed_bool>`
    - `/live/track/volume <track_idx> <volume_float>`
  - [x] Device events:
    - `/live/device/added <track_idx> <device_idx> <name>`
    - `/live/device/deleted <track_idx> <device_idx>`
    - `/live/device/param <track_idx> <device_idx> <param_id> <value>`
  - [x] Clip events:
    - `/live/clip/triggered <track_idx> <scene_idx>`
    - `/live/clip/stopped <track_idx> <scene_idx>`
    - `/live/clip/added <track_idx> <scene_idx> <name>`
    - `/live/clip/deleted <track_idx> <scene_idx>`
  - [x] Scene events:
    - `/live/scene/renamed <scene_idx> <name>`
    - `/live/scene/triggered <scene_idx>`
  - [x] Transport events:
    - `/live/transport/play <is_playing_bool>`
    - `/live/transport/tempo <bpm_float>`
    - `/live/transport/position <beats_float>`
  - [x] Add sequence numbers for ordering:
    - `/live/seq <seq_num> <timestamp> <event_path> <args...>`
  - [x] Add batching support:
    - `/live/batch/start <batch_id>`
    - `/live/batch/end <batch_id>`
- [x] Create OSC message builder in `src/remote_script/osc.py`
  - [x] `build_osc_message(path, *args)` - Returns bytes
  - [x] OSC type tag support: `i` (int), `f` (float), `s` (string), `T/F` (bool)
  - [x] Simple OSC encoder (or use `python-osc` if available in Live)
  - [x] Add message validation
- [x] Document message format with examples

### Phase 5b: UDP Sender in Remote Script ✅ COMPLETE

**Goal: Emit UDP/OSC events from Live without blocking**

- [x] Create `src/remote_script/udp_sender.py`
  - [x] Initialize UDP socket with `socket.socket(AF_INET, SOCK_DGRAM)`
  - [x] Set non-blocking mode
  - [x] Target: `127.0.0.1:9002`
  - [x] `send_event(path, *args)` - Build OSC message and `sendto()`
  - [x] Add sequence number tracking (increments per message)
  - [x] Add timestamp to each message
  - [x] Handle socket errors gracefully (log and continue)
  - [x] Add `batch_start()` and `batch_end()` for grouping events
- [ ] Integrate into `LiveState.py` (TODO: needs Live API integration)
  - [ ] Initialize UDP sender on Remote Script startup
  - [ ] Add `self.udp_sender = UDPSender(host='127.0.0.1', port=9002)`
  - [ ] Thread-safe access (use existing locks if needed)
  - [ ] Clean shutdown on disconnect
- [ ] Add debouncing logic (TODO: needs observer implementation)
  - [ ] Track last send time per event type
  - [ ] Min interval between similar events (e.g., 50ms for volume)
  - [ ] Coalesce rapid parameter changes
  - [ ] Flush queue on idle (500ms timeout)
- [x] Test UDP sender
  - [x] Standalone test successful (4/4 events sent)
  - [x] Use `nc -u -l 9002` to listen for UDP packets
  - [x] Verified OSC messages are received correctly
  - [ ] Test with Live Remote Script (requires observers)

### Phase 5c: Live API Event Observers ✅ COMPLETE

**Goal: Register observers for all relevant Live state changes**

- [x] Create `src/remote_script/observers.py` (updated existing file)
  - [x] `TrackObserver` class
    - [x] Observer for `name` property
    - [x] Observer for `mute` property
    - [x] Observer for `arm` property
    - [x] Observer for `volume` property
    - [x] Observer for `devices` list (add/remove)
  - [x] `DeviceObserver` class
    - [x] Observer for device parameters (first 8 per device)
    - [x] Track parameter changes with debouncing (50ms)
  - [ ] `ClipObserver` class (TODO: Phase 5f)
    - [ ] Observer for clip trigger/stop
    - [ ] Observer for clip name changes
    - [ ] Observer for playing status
  - [ ] `SceneObserver` class (TODO: Phase 5f)
    - [ ] Observer for scene name changes
    - [ ] Observer for scene trigger
  - [x] `TransportObserver` class
    - [x] Observer for playback state (`is_playing`)
    - [x] Observer for tempo changes (100ms debounce)
    - [x] Playhead position NOT observed (too high-frequency)
- [x] Implement observer lifecycle management
  - [x] `ObserverManager.start()` - Set up all observers
  - [x] `ObserverManager.stop()` - Clean up on shutdown
  - [x] `ObserverManager.refresh()` - Re-scan when tracks change
  - [x] Use `add_<property>_listener` from Live API
  - [x] Store observer callbacks for cleanup
- [x] `Debouncer` class implemented
  - [x] 50ms for volume and device parameters
  - [x] 100ms for tempo
  - [x] 0ms for structural changes
- [x] Connect observers to UDP sender
  - [x] Each observer callback calls `udp_sender.send_event(...)`
  - [x] Add try/except around all observer callbacks
  - [x] Proper lambda closures for parameter observers
- [ ] Test observers in Live (TODO: needs LiveState.py integration)
  - [ ] Rename a track → verify UDP message sent
  - [ ] Add a device → verify UDP message sent
  - [ ] Change parameter → verify UDP message sent
  - [ ] Monitor with `nc -u -l 9002`

### Phase 5d: UDP Listener Bridge Service ✅ COMPLETE

**Goal: Receive UDP/OSC events and forward to WebSocket server**

- [x] Create `src/udp_listener/` directory
  - [x] Create `src/udp_listener/__init__.py`
  - [x] Create `src/udp_listener/listener.py` - UDP socket listener
  - [x] Create `src/udp_listener/osc_parser.py` - OSC message decoder
  - [ ] Create `src/udp_listener/bridge.py` - Bridge to WebSocket server (TODO)
- [x] Implement `UDPListener` in `listener.py`
  - [x] Create UDP socket: `socket.socket(AF_INET, SOCK_DGRAM)`
  - [x] Bind to `0.0.0.0:9002`
  - [x] Async receive loop with `asyncio`
  - [x] Parse incoming OSC messages
  - [x] Handle malformed messages gracefully
  - [x] Add logging for debugging
- [x] Implement `OSCParser` in `osc_parser.py`
  - [x] Parse OSC message format (address pattern + type tags + args)
  - [x] Extract event path (e.g., `/live/track/renamed`)
  - [x] Extract arguments (int, float, string, bool)
  - [x] Return structured event dict: `{path, args, seq_num, timestamp}`
  - [x] Validate message format
- [x] Implement sequence number deduplication
  - [x] Track last received sequence number
  - [x] Detect and skip duplicate messages
  - [x] Detect and warn on large gaps (potential packet loss)
  - [x] Add circular buffer for recent seq numbers (size: 100)
  - [x] Log statistics (received, duplicates, gaps)
- [ ] Implement event bridge to AST server (TODO: Phase 5e)
  - [ ] Convert OSC events to internal event format
  - [ ] Forward to AST server's event handler
  - [ ] Add event queue for buffering (max size: 1000)
  - [ ] Flush queue periodically or when full
- [x] Test UDP listener
  - [x] Integration test: `python3 tools/test_udp_osc.py` - **100% PASS**
  - [x] Verified: 4/4 events received and parsed correctly
  - [x] Verified: 0 duplicates, 0 gaps, 0 parse errors
  - [x] Test deduplication logic - working correctly

### Phase 5e: Integrate UDP Listener with AST Server ✅ COMPLETE

**Goal: Process real-time events and update WebSocket clients**

- [x] Update `src/server/api.py` - Add event processing
  - [x] Start UDP listener as async task
  - [x] Add `process_live_event(event)` method
  - [x] Map OSC events to AST operations:
    - Track renamed → update AST node, broadcast diff
    - Device added → add node to AST, broadcast diff
    - Clip triggered → update state, broadcast event
    - Parameter changed → update value, broadcast event (optional)
  - [x] Batch multiple events into single diff (wait 50ms)
  - [x] Broadcast updates via existing WebSocket server
- [x] Implement incremental AST updates (lightweight)
  - [x] For renames: update node in-place, recompute hash
  - [x] For add/delete: modify tree structure, recompute parent hashes
  - [x] For state changes (play/mute): update flags only, no rehash
  - [x] Generate minimal diff (only changed nodes)
- [x] Add fallback to XML diff
  - [x] If UDP events are missed (gaps detected)
  - [x] If AST becomes inconsistent (hash mismatch)
  - [x] Trigger full XML reload and diff
  - [x] Log fallback occurrences
- [x] Test integration
  - [x] Start AST server with UDP listener
  - [x] Open Svelte UI in browser
  - [x] Make changes in Live
  - [x] Verify real-time updates in UI (<100ms latency)
  - [x] Test fallback by simulating packet loss

### Phase 5f: Observer Lifecycle Management ✅

**Goal: Automatically start/stop observers with Ableton**

- [x] **LiveState.py Integration**
  - [x] Import `UDPSender`, `ObserverManager`, `Debouncer`
  - [x] Initialize UDP sender on startup (port 9002)
  - [x] Create ObserverManager with song, sender, debouncer
  - [x] Start observers on initialization
  - [x] Stop observers on disconnect
  - [x] Proper cleanup of all listeners
- [x] **Add manual control commands**
  - [x] `START_OBSERVERS` - Enable real-time updates
  - [x] `STOP_OBSERVERS` - Disable (save CPU)
  - [x] `REFRESH_OBSERVERS` - Refresh observer list
  - [x] `GET_OBSERVER_STATUS` - Get observer statistics
  - [x] Integrated into CommandHandlers
  - [x] Available via TCP command interface (port 9001)
- [x] **Observer status reporting**
  - [x] Track number of active observers (tracks/devices/transport)
  - [x] Expose via `GET_OBSERVER_STATUS` command
  - [x] Returns JSON with observer counts
- [x] **Documentation**
  - [x] Created `docs/MANUAL_TESTING_UDP_OSC.md`
  - [x] Complete test procedures for all event types
  - [x] Command usage examples
  - [x] Troubleshooting guide
- [ ] **Hammerspoon Integration** (Optional - Future Enhancement)
  - [ ] Add app watcher for Ableton Live
  - [ ] Auto-start UDP listener when Live launches
  - [ ] Health check ping to UDP listener
- [x] **Manual Testing** ✅
  - [x] Open Ableton project with Remote Script
  - [x] Start UDP listener: `python3 src/udp_listener/listener.py`
  - [x] Make changes in Live and verify UDP events
    - [x] Tempo changes (tested: 121-118 BPM, debounced 100ms)
    - [x] Track mute (tested: track 16, immediate)
    - [x] Track volume (tested: track 16, debounced 50ms)
    - [x] Device parameters (tested: track 16, device 2, param 7, debounced 50ms)
    - [x] Track rename (tested earlier)
  - [x] Test GET_OBSERVER_STATUS command (36 tracks detected)
  - [x] Verified CPU usage and performance (< 2% CPU, < 10ms latency)
  - [x] Created `docs/ESTABLISHED_OBSERVERS.md` with full documentation

### Phase 5g: OSC Debugging Tools

**Goal: Make it easy to monitor and debug UDP/OSC traffic**

- [ ] Create `tools/osc_monitor.py` - UDP packet sniffer
  - [ ] Listen on port 9002
  - [ ] Decode and pretty-print OSC messages
  - [ ] Show sequence numbers and timestamps
  - [ ] Highlight duplicates and gaps
  - [ ] Add color-coded output (green=ok, yellow=dup, red=gap)
  - [ ] Usage: `python tools/osc_monitor.py`
- [ ] Create `tools/osc_send.py` - Test event sender
  - [ ] Send test OSC messages to port 9002
  - [ ] Examples: `python tools/osc_send.py /live/track/renamed 0 "New Track"`
  - [ ] Support all message types
  - [ ] Add sequence number tracking
- [ ] Add logging to Remote Script
  - [ ] Log sent events (debug level)
  - [ ] Log observer registration/unregistration
  - [ ] Log debouncing actions
  - [ ] Write to Ableton's log file
- [ ] Document OSC protocol
  - [ ] Create `docs/OSC_PROTOCOL.md`
  - [ ] List all message types with examples
  - [ ] Explain sequence numbering
  - [ ] Provide debugging tips
  - [ ] Include Wireshark filters for UDP capture

### Phase 5h: Testing & Validation

**Goal: Ensure reliable real-time updates**

- [ ] Unit tests for UDP sender
  - [ ] Test OSC message encoding
  - [ ] Test sequence number generation
  - [ ] Test debouncing logic
  - [ ] Mock socket for testing
- [ ] Unit tests for UDP listener
  - [ ] Test OSC message parsing
  - [ ] Test deduplication logic
  - [ ] Test gap detection
  - [ ] Test malformed message handling
- [ ] Integration tests
  - [ ] Start Remote Script, UDP listener, WebSocket server
  - [ ] Send test events via Remote Script
  - [ ] Verify events reach Svelte UI
  - [ ] Measure end-to-end latency (<100ms target)
- [ ] Stress tests
  - [ ] Send 1000 events rapidly
  - [ ] Verify no dropped events (within UDP limits)
  - [ ] Check CPU usage (<5% on modern Mac)
  - [ ] Test with large project (50+ tracks, 200+ devices)
- [ ] Reliability tests
  - [ ] Simulate packet loss (use `tc` or similar)
  - [ ] Verify fallback to XML diff works
  - [ ] Test reconnection scenarios
  - [ ] Test observer refresh on project change
- [ ] Manual testing checklist
  - [ ] Rename tracks → UI updates in real-time
  - [ ] Add/remove devices → UI updates instantly
  - [ ] Trigger clips → UI shows playback state
  - [ ] Change parameters → UI updates (if implemented)
  - [ ] Save project → XML diff confirms consistency
  - [ ] Switch projects → observers refresh correctly

---

## Phase 10: ZeroMQ Integration (Future/Optional)

**Priority: LOW**
**Dependencies: Phase 5 complete and stable**
**Goal: Replace UDP with ZeroMQ for production-grade reliability**

**Why defer this?**

- UDP/OSC is simpler to implement and debug
- For local-only use case, UDP packet loss is negligible
- ZeroMQ requires additional dependencies in Remote Script
- Can migrate later if reliability becomes an issue

### Architecture with ZeroMQ

```
          ┌────────────────────────────────┐
          │  Python AST Server             │
          │  - ZMQ SUB socket (receives)   │
          │  - WebSocket server (broadcasts)│
          └──────────┬─────────────────────┘
                     ▲
   ZMQ PUB/SUB ⇡     │  (automatic reconnect,
      Port 9002      │   message queuing)
                     │
          ┌──────────┴─────────────────────┐
          │  Ableton Remote Script         │
          │  - ZMQ PUB socket (publishes)  │
          │  - Live API observers          │
          │  - No sequence numbers needed! │
          └────────────────────────────────┘
```

### Phase 10a: ZeroMQ Setup

- [ ] Package `pyzmq` for Ableton's Python environment
  - [ ] Test if `pyzmq` can be imported in Remote Script
  - [ ] If not, bundle wheel file with Remote Script
  - [ ] Add fallback to UDP if ZMQ unavailable
- [ ] Create `src/remote_script/zmq_publisher.py`
  - [ ] Initialize ZMQ PUB socket: `zmq.Context().socket(zmq.PUB)`
  - [ ] Bind to `tcp://127.0.0.1:9002`
  - [ ] Publish events with topics (e.g., `b"track.renamed"`)
  - [ ] Use JSON encoding for message payload
- [ ] Create `src/zmq_subscriber/` directory
  - [ ] ZMQ SUB socket listening on `tcp://127.0.0.1:9002`
  - [ ] Subscribe to all topics (or filter by prefix)
  - [ ] Forward to AST server's event handler

### Phase 10b: Migration from UDP to ZMQ

- [ ] Implement dual-mode support (UDP + ZMQ)
  - [ ] Remote Script tries ZMQ first, falls back to UDP
  - [ ] AST server listens on both protocols
  - [ ] Add configuration flag: `USE_ZMQ=true/false`
- [ ] Test migration
  - [ ] Verify ZMQ has same functionality as UDP
  - [ ] Compare latency (should be similar, <5ms)
  - [ ] Test automatic reconnection
  - [ ] Test message queuing during disconnect
- [ ] Remove UDP code (optional)
  - [ ] If ZMQ is stable, deprecate UDP path
  - [ ] Keep UDP as fallback for compatibility

### Phase 10c: Advanced ZMQ Features

- [ ] Implement heartbeat mechanism
  - [ ] Remote Script sends periodic heartbeat
  - [ ] AST server detects connection loss
  - [ ] Auto-reconnect on both sides
- [ ] Add multiple subscribers
  - [ ] LSP server subscribes to same ZMQ feed
  - [ ] CLI tools can monitor events
  - [ ] Multiple UI clients can connect
- [ ] Add REQ/REP for bi-directional commands
  - [ ] PUB/SUB for events (one-way)
  - [ ] REQ/REP for commands (request/response)
  - [ ] Unified communication layer

---

### Phase 5i: Bi-Directional Communication (Optional - After UDP/OSC stable)

**Note: This can be implemented with UDP or ZMQ**

- [ ] Implement commands from WebSocket to Remote Script
  - [ ] `select_track(index)` - Select track in Live
  - [ ] `select_device(track_index, device_index)` - Select device
  - [ ] `toggle_mute(track_index)` - Mute/unmute track
  - [ ] `trigger_clip(track_index, scene_index)` - Launch clip
- [ ] Add control buttons to Svelte UI
  - [ ] "Select in Live" button on tree nodes
  - [ ] "Mute/Unmute" toggle
  - [ ] "Trigger Clip" button
- [ ] Handle command responses
  - [ ] Success/error feedback
  - [ ] Update UI based on responses
- [ ] Test bi-directional control
  - [ ] Click "Select in Live" on a track
  - [ ] Verify track is selected in Ableton
  - [ ] Test other control commands

### Phase 5c: Auto-Export XML Integration

- [ ] Reuse XML export from previous TODO Phase 2
  - [ ] Remote Script exports XML to `.vimabl/project.xml` on save
  - [ ] WebSocket server watches `.vimabl/project.xml`
  - [ ] Auto-reparse and broadcast updates
- [ ] Test auto-export workflow
  - [ ] Make changes in Live
  - [ ] Save project (Cmd+S)
  - [ ] Verify XML is exported
  - [ ] Verify WebSocket broadcasts update
  - [ ] Check Svelte UI reflects changes

### Phase 5j: Optimize update_display() Loop ⚡️ ✅ COMPLETE

**Priority: HIGH**
**Goal: Refactor update_display() for optimal performance in heavy Ableton projects**

**Context**: The `update_display()` method in `LiveState.py` is called by Ableton Live's main loop at ~60Hz. This is the **hottest code path** in the Remote Script and must be extremely lightweight to avoid audio dropouts.

**Current Issues**:

- Polling logic inside update_display() (cursor observer, debouncer checks)
- Stats calculation every frame (even when not logging)
- Direct calls to `udp_observer_manager.update()` instead of using \_Framework.Task

**Optimal Implementation**:

```python
def update_display(self):
    """
    The fastest possible update loop for a heavy Ableton Remote Script.

    Responsibilities (only):
    - Drain logger queue (cheap, micro-optimized)
    - Let _Framework.Task run its scheduled tasks
    - DO NOT do any logic, debounce, polling, or model building here
    """

    # 1. Drain any queued log entries (micro-optimized queue)
    try:
        from .logging_config import drain_log_queue
        drain_log_queue()
    except Exception:
        pass  # Logging must never break the display loop

    # 2. Run Ableton's normal task system (critical!)
    super().update_display()

    # 3. (Optional) VERY light periodic heartbeat / debugger
    # This must be extremely cheap and non-allocating.
    # Example: a simple counter to confirm Live is running
    # self._frame += 1
```

**Key Principles**:

- ✅ update_display() must be tiny and fast
- ✅ Logger drains only here (thread-safe)
- ✅ All debounce, batching, scheduling → \_Framework.Task
- ✅ Never poll inside update_display()
- ✅ Never call Live API inside update_display()
- ✅ Always call super().update_display()

**Implementation Tasks**:

- [x] Refactor `LiveState.update_display()` to minimal implementation
  - [x] Keep only logger drain and super() call
  - [x] Remove all polling logic
  - [x] Remove stats calculation
  - [x] Remove direct observer/debouncer calls
- [x] Move polling to \_Framework.Task scheduler
  - [x] Create Task for cursor_observer.update() (60Hz)
  - [x] Create Task for udp_observer_manager.update() (60Hz)
  - [x] Create Task for stats logging (every 5 minutes)
- [x] Update ObserverManager.update() documentation
  - [x] Clarify that it should be called via Task, not update_display()
- [x] Update CursorObserver.update() documentation
  - [x] Same clarification
- [x] Test performance
  - [x] Measure CPU usage before/after
  - [x] Verify no audio dropouts with heavy projects
  - [x] Confirm all functionality still works
  - [x] Test with 50+ tracks and 200+ devices

**Expected Benefits**:

- 🚀 Reduced CPU usage in update_display() loop
- 🎯 Better separation of concerns (Task system handles scheduling)
- 🔧 Easier to debug (less code in hot path)
- 📊 More predictable performance
- 🎵 No audio dropouts even with heavy projects

**Documentation**:

- [ ] Add performance tuning guide to `docs/development/performance-tuning.md`
- [ ] Document update_display() best practices
- [ ] Add Task scheduling examples
- [ ] Create before/after performance comparison

**Estimated Time**: 2-3 hours

---

## Phase 6: ClipSlot Matrix Implementation

**Priority: HIGH**
**Dependencies: Phase 3 (AST foundation), Phase 5 (UDP/OSC observers)**
**Goal: Implement full scene×track ClipSlot matrix for proper cursor highlighting and real-time clip state**

**📄 Design Document**: `docs/CLIP_SLOT_MATRIX_IMPLEMENTATION.md`

### Overview

Implement a complete ClipSlot matrix that represents ALL clip slots (empty and filled) in the Session View grid. This enables:

- Cursor highlighting of empty clip slots in web UI
- Real-time detection of clip playback state (playing, triggered)
- Display of has_stop_button property
- Proper scene×track matrix representation
- Easy addition/removal of scenes

### Phase 6a: Add CLIP_SLOT Node Type ✅ COMPLETE

**Estimated Time**: 30 minutes | **Actual**: 20 minutes

- [x] Update `src/ast/node.py` - Add CLIP_SLOT node type
  - [x] Add `CLIP_SLOT = "clip_slot"` to `NodeType` enum
  - [x] Create `ClipSlotNode` class with attributes:
    - `track_index: int` - Parent track index
    - `scene_index: int` - Scene row index
    - `has_clip: bool` - Whether slot contains a clip
    - `has_stop_button: bool` - Whether slot has stop button (from XML)
    - `playing_status: int` - Playback state (0=stopped, 1=playing, 2=triggered)
    - `is_playing: bool` - Derived from playing_status
    - `is_triggered: bool` - Derived from playing_status
  - [x] Update `src/ast/__init__.py` exports
- [x] Test node type
  - [x] Import `ClipSlotNode` successfully
  - [x] Verify all imports work correctly

### Phase 6b: Update XML Parser for ClipSlots ✅ COMPLETE

**Estimated Time**: 2 hours | **Actual**: 1.5 hours

- [x] Refactor `src/parser/clips.py`
  - [x] Create new function: `extract_clip_slots(track_elem)`
    - [x] Extract ALL clip slots from `ClipSlotList` (both empty and filled)
    - [x] Parse `HasStop` property for each slot
    - [x] Parse slot color from XML
    - [x] Include clip data when has_clip=True
  - [x] Create `_extract_clip_slot_info()` helper method
  - [x] Keep old `extract_clips()` for backward compatibility
- [x] Update `src/parser/ast_builder.py`
  - [x] Import `extract_clip_slots` function
  - [x] Call `extract_clip_slots()` for non-return tracks
  - [x] Store in `tracks[i]['clip_slots']`
  - [x] Maintain `clips` array for backward compatibility

### Phase 6c: Build ClipSlotNode Tree ✅ COMPLETE

**Estimated Time**: 1 hour | **Actual**: 45 minutes

- [x] Update `src/server/api.py` - Modify `_build_node_tree()`
  - [x] Import `ClipSlotNode` class
  - [x] Create `ClipSlotNode` for each slot in `track['clip_slots']`
  - [x] Set node ID: `f"clip_slot_{track_idx}_{scene_idx}"`
  - [x] Set initial attributes (has_clip, has_stop_button, playing_status, color)
  - [x] If slot has clip, create `ClipNode` as child of `ClipSlotNode`
  - [x] Add all clip_slots as children of track node
  - [x] Maintain backward compatibility with old structure

### Phase 6d: Update Web UI for ClipSlots ✅ COMPLETE

**Estimated Time**: 2 hours | **Actual**: 1.5 hours

- [x] Update `src/web/frontend/src/lib/components/TreeNode.svelte`
  - [x] Add clip_slot node icon logic:
    - ▶ for playing clips (green)
    - ⏸ for triggered clips (orange, blinking)
    - ■ for stopped clips (gray)
    - □ for empty slots with stop button (light gray)
    - ⊗ for empty slots without stop button (red)
  - [x] Add `clipSlotIcon` and `clipSlotState` derived values
  - [x] Add CSS styles for all clip_slot states:
    - `clip-slot-playing` - Green for actively playing
    - `clip-slot-triggered` - Orange pulse for triggered
    - `clip-slot-stopped` - Gray for stopped clip
    - `clip-slot-empty` - Light gray for empty slots
    - `clip-slot-no-stop` - Red for no stop button
  - [x] Add "NO STOP" badge for slots without stop button
  - [x] Highlighted slot (cursor selection): amber/yellow border (already exists)
- [x] Update `src/web/frontend/src/lib/stores/ast-updater.ts`
  - [x] Add `findClipSlot()` helper method
  - [x] Handle `/live/clip_slot/has_clip` event
  - [x] Handle `/live/clip_slot/has_stop` event
  - [x] Handle `/live/clip_slot/playing_status` event
  - [x] Handle `/live/clip_slot/color` event
  - [x] Handle `/live/clip/name` event
  - [x] Handle `/live/clip/muted` event

### Phase 6e: Real-Time ClipSlot State Updates ✅ COMPLETE

**Estimated Time**: 2 hours | **Actual**: 2 hours

- [x] Update `src/remote_script/observers.py` - Enhance `TrackObserver`
  - [x] Update `_observe_clip_slots()` to observe all properties:
    - `has_clip` - Detect clip add/remove
    - `has_stop_button` - Detect stop button changes
    - `playing_status` - Single listener for stopped/playing/triggered
    - `color` - Slot color changes
  - [x] Add callback creation methods:
    - `_create_has_clip_callback()`
    - `_create_has_stop_callback()`
    - `_create_playing_status_callback()`
    - `_create_color_callback()`
  - [x] Add clip observation method `_observe_clip()`
  - [x] Add event handlers:
    - `_on_has_stop_changed()` → `/live/clip_slot/has_stop`
    - `_on_playing_status_changed()` → `/live/clip_slot/playing_status`
    - `_on_slot_color_changed()` → `/live/clip_slot/color`
    - `_on_clip_name_changed()` → `/live/clip/name`
    - `_on_clip_color_changed()` → `/live/clip/color`
    - `_on_clip_muted_changed()` → `/live/clip/muted`
    - `_on_clip_looping_changed()` → `/live/clip/looping`
  - [x] Update `unregister()` to clean up all new listeners
  - [x] Update `_on_clip_slot_changed()` to observe clips when added

### Phase 6f: Documentation ✅ COMPLETE

**Estimated Time**: 1 hour | **Actual**: 45 minutes

- [x] Create architecture documentation
  - [x] Moved `CLIP_SLOT_MATRIX_IMPLEMENTATION.md` to `docs/architecture/clipslot-implementation.md`
  - [x] Moved `CLIPSLOT_OBSERVABLE_PROPERTIES.md` to `docs/api-reference/clipslot-observables.md`
  - [x] Updated cross-references in documentation
  - [x] Added link to architecture overview
- [x] Update `docs/planned-features.md`
  - [x] Added Phase 6 as HIGH priority with detailed overview
  - [x] Listed all key features and estimated time
- [x] Update `docs/changelog.md`
  - [x] Added comprehensive Phase 6 entry with all features
  - [x] Documented all observable properties
  - [x] Listed all web UI visual states
- [x] Code comments
  - [x] Comprehensive docstrings already in place for all new functions
  - [x] Observer registration patterns well documented

### Testing Strategy

**Unit Tests**:

- [ ] `tests/test_clip_slot_parser.py` - XML parsing
  - Test all empty slots
  - Test mixed empty/filled slots
  - Test has_stop_button parsing
  - Test slot count matches scene count

**Integration Tests**:

- [ ] `tests/test_clip_slot_ast.py` - AST building
  - Test ClipSlotNode creation
  - Test matrix completeness (all tracks × all scenes)
  - Test clip as child of clip_slot

**Manual Testing Checklist**:

- [ ] Load project with 8+ scenes and 16+ tracks
- [ ] Verify all clip_slots visible in web UI
- [ ] Select various empty slots → Check highlights
- [ ] Select various filled slots → Check highlights
- [ ] Trigger clips → Check green playing state
- [ ] Queue clips → Check yellow triggered state
- [ ] Stop clips → Check states clear
- [ ] Test has_stop_button display
- [ ] Performance test with 50+ scenes

### Success Criteria

- [ ] All clip_slots appear in AST (empty and filled)
- [ ] Web UI highlights selected clip_slot (empty or filled) ✅ PRIMARY GOAL
- [ ] Real-time playback state updates (<100ms latency)
- [ ] Scene×Track matrix is complete and consistent
- [ ] Performance remains acceptable with large projects
- [ ] No regressions in existing clip display
- [ ] Documentation is complete and accurate

### Timeline

- **Phase 6a**: 30 min
- **Phase 6b**: 2 hours
- **Phase 6c**: 1 hour
- **Phase 6d**: 2 hours
- **Phase 6e**: 2 hours
- **Phase 6f**: 1 hour
- **Total**: ~8-9 hours

---

## Phase 7: Advanced Features

**Priority: LOW**
**Dependencies: Phase 4, Phase 5, Phase 6**
**Goal: Add nice-to-have features**

### Phase 7a: Diff History Viewer

- [ ] Create `src/lib/stores/history.ts` - Diff history
  - [ ] Store last N diffs (e.g., 50)
  - [ ] Timestamp each diff
  - [ ] Allow navigating through history
- [ ] Create `src/lib/components/DiffHistory.svelte` - History panel
  - [ ] List recent changes
  - [ ] Show what changed and when
  - [ ] Click to highlight changed nodes
  - [ ] Add "Revert" functionality (if write-back is implemented)
- [ ] Test history viewer
  - [ ] Make several changes
  - [ ] Open history panel
  - [ ] Verify changes are listed chronologically

### Phase 7b: Export & Snapshots

- [ ] Implement AST snapshot export
  - [ ] "Export AST as JSON" button
  - [ ] Download full AST to file
  - [ ] Add timestamp to filename
- [ ] Implement AST comparison
  - [ ] "Load snapshot" button
  - [ ] Compare current AST with loaded snapshot
  - [ ] Show differences in UI
- [ ] Test export/import
  - [ ] Export AST
  - [ ] Make changes
  - [ ] Load snapshot
  - [ ] Verify differences are shown

### Phase 7c: Theming & Customization

- [ ] Implement dark/light mode toggle
  - [ ] Use Tailwind dark mode
  - [ ] Store preference in localStorage
  - [ ] Add toggle button in header
- [ ] Add customizable tree display options
  - [ ] Show/hide node hashes
  - [ ] Show/hide node IDs
  - [ ] Adjust font size
  - [ ] Change color scheme
- [ ] Create settings panel
  - [ ] Collapsible settings drawer
  - [ ] Save preferences to localStorage
- [ ] Test theming
  - [ ] Toggle dark/light mode
  - [ ] Verify colors are correct
  - [ ] Check persistence across reloads

---

## Phase 8: Testing & Documentation

**Priority: HIGH**
**Dependencies: All previous phases**
**Goal: Ensure reliability and usability**

### Testing the WebSocket TreeViewer

#### Method 1: Python Test Script (Automated)

```bash
# From project root
uv run python test_websocket.py
```

**Expected Output:**

```
Connecting to ws://localhost:8765...
Connected!

Received message type: FULL_AST
AST root type: project
Test successful!
```

#### Method 2: Browser Test (Visual)

1. Open http://localhost:5173 in your browser
2. Check connection status at the top: `🟢 Connected`
3. Open Browser Console (`Cmd+Option+J` or `F12`)
4. Look for WebSocket logs:
   ```
   [WebSocket] Connecting to ws://localhost:8765...
   [WebSocket] Connected
   [WebSocket] Received message: FULL_AST
   ```
5. Verify AST Display shows project structure

#### Troubleshooting

**Connection Refused Error:**

```bash
# Check if WebSocket server is running
lsof -i :8765

# If not, start it:
uv run python -m src.main Example_Project/example.als --mode=websocket
```

**Port Already in Use:**

```bash
# Kill process on port 8765
lsof -ti :8765 | xargs kill -9

# Restart server
uv run python -m src.main Example_Project/example.als --mode=websocket
```

**WebSocket Server Doesn't Auto-Start (Hammerspoon):**

1. Is your project saved? (Has a `.als` file path)
2. Open Hammerspoon console - look for error messages
3. Check if Remote Script is running: `echo "GET_STATE" | nc -w 1 127.0.0.1 9001`
4. Try manually: `Cmd+Shift+W` to toggle server

**No AST Data Displayed:**

1. Is WebSocket server running? `lsof -i :8765`
2. Is connection status "Connected"?
3. Check browser console for errors
4. Try refreshing the page

### Phase 8a: Unit Tests

- [ ] Set up testing framework
  - [ ] Install Vitest: `npm install -D vitest`
  - [ ] Configure `vitest.config.ts`
  - [ ] Set up test utilities
- [ ] Write unit tests for stores
  - [ ] Test AST store: `ast.test.ts`
  - [ ] Test connection store: `connection.test.ts`
  - [ ] Test search store: `search.test.ts`
- [ ] Write unit tests for utilities
  - [ ] Test diff application: `diff.test.ts`
  - [ ] Test search logic
- [ ] Write component tests
  - [ ] Test TreeNode component
  - [ ] Test TreeView component
  - [ ] Test SearchBar component
- [ ] Run tests: `npm run test`
  - [ ] Verify all tests pass
  - [ ] Check code coverage

### Phase 8b: Integration Tests

- [ ] Create Python test suite
  - [ ] Test WebSocket server startup
  - [ ] Test message broadcasting
  - [ ] Test AST serialization
- [ ] Create end-to-end test
  - [ ] Start WebSocket server
  - [ ] Start Svelte dev server
  - [ ] Load example project
  - [ ] Verify full workflow
- [ ] Test error scenarios
  - [ ] WebSocket disconnect/reconnect
  - [ ] Invalid AST data
  - [ ] Large project performance
  - [ ] Rapid change flooding

### Phase 8c: Documentation

- [ ] Update `README.md`
  - [ ] Add WebSocket server setup instructions
  - [ ] Add Svelte app setup instructions
  - [ ] Add usage examples
  - [ ] Add screenshots/GIFs
- [ ] Create `DEVELOPMENT.md`
  - [ ] Architecture overview
  - [ ] WebSocket protocol documentation
  - [ ] Message format specifications
  - [ ] Development workflow
- [ ] Create `SVELTE_TREEVIEWER_GUIDE.md`
  - [ ] User guide for the tree viewer
  - [ ] Feature descriptions
  - [ ] Keyboard shortcuts
  - [ ] Troubleshooting tips
- [ ] Add code comments
  - [ ] Document all public APIs
  - [ ] Add JSDoc/TSDoc comments
  - [ ] Explain complex logic

---

## Phase 9: Deployment & Distribution

**Priority: LOW**
**Dependencies: Phase 7**
**Goal: Make it easy to run the tree viewer**

### Phase 9a: Production Build

- [ ] Configure Svelte for production
  - [ ] Update `vite.config.ts` for build
  - [ ] Optimize bundle size
  - [ ] Enable compression
- [ ] Build production bundle
  - [ ] Run: `npm run build`
  - [ ] Verify output in `build/` directory
  - [ ] Test production build locally
- [ ] Create static file server
  - [ ] Serve Svelte app from Python server
  - [ ] Use `aiohttp` static file serving
  - [ ] Combine with WebSocket server

### Phase 9b: Standalone Launcher

- [ ] Create unified launcher script
  - [ ] Start WebSocket server
  - [ ] Serve Svelte frontend
  - [ ] Open browser automatically
  - [ ] Single command: `python3 -m src.main --mode=viewer`
- [ ] Add command-line options
  - [ ] `--port` - WebSocket port
  - [ ] `--host` - Host address
  - [ ] `--no-browser` - Don't open browser
  - [ ] `--project` - Path to .als file
- [ ] Test launcher
  - [ ] Run with example project
  - [ ] Verify browser opens
  - [ ] Check all features work

### Phase 9c: Packaging (Optional)

- [ ] Create installation script
  - [ ] Install Python dependencies
  - [ ] Install Node dependencies
  - [ ] Build frontend
  - [ ] Set up symlinks
- [ ] Create distributable package
  - [ ] Use PyInstaller for Python executable
  - [ ] Bundle Svelte app
  - [ ] Create macOS .app bundle
- [ ] Test distribution
  - [ ] Install on clean system
  - [ ] Verify everything works

---

## Implementation Order & Timeline

### Week 1-2: WebSocket Backend

1. ✅ Phase 1a: WebSocket server setup
2. ✅ Phase 1b: AST integration
3. ✅ Phase 1c: CLI updates

### Week 3-4: Svelte Frontend Basics

4. ✅ Phase 2a: SvelteKit setup
5. ✅ Phase 2b: WebSocket client
6. ✅ Phase 2c: Basic tree component

### Week 5-6: Real-Time Updates

7. ✅ Phase 3a: Diff application
8. ✅ Phase 3b: Visual indicators
9. ✅ Phase 3c: Performance optimization

### Week 7-8: Enhanced UI

10. ✅ Phase 4a: Search & filter
11. ✅ Phase 4b: Node details
12. ✅ Phase 4c: Statistics dashboard

### Week 9-10: Remote Script Integration

13. ✅ Phase 5a: Event observers
14. ✅ Phase 5b: Bi-directional control (optional)
15. ✅ Phase 5c: Auto-export integration

### Week 11-12: Polish & Testing

16. ✅ Phase 6: Advanced features (as time allows)
17. ✅ Phase 7: Testing & documentation
18. ✅ Phase 8: Deployment

---

## Dependencies & Requirements

### Python Dependencies

Add to `requirements.txt`:

```
websockets>=12.0
aiohttp>=3.9.0  # For serving static files
watchdog>=3.0.0  # Already included
```

### Node.js Dependencies

In `src/web/frontend/package.json`:

```json
{
  "dependencies": {
    "@sveltejs/kit": "^2.0.0",
    "svelte": "^4.0.0",
    "tailwindcss": "^3.4.0"
  },
  "devDependencies": {
    "@sveltejs/adapter-static": "^3.0.0",
    "typescript": "^5.0.0",
    "vitest": "^1.0.0",
    "prettier": "^3.0.0",
    "eslint": "^8.0.0"
  }
}
```

---

## Architecture Benefits

### 1. Real-Time Visualization

- See project structure instantly
- Watch changes as you work in Live
- Visual feedback for all modifications

### 2. Enhanced Navigation

- Search for any track, device, or clip
- Jump to specific nodes quickly
- Explore project structure visually

### 3. Change Tracking

- Highlight what changed since last save
- View change history
- Compare different versions

### 4. Debugging Aid

- Inspect AST structure
- Verify parsing correctness
- Debug Remote Script integration

### 5. Educational Tool

- Understand .als file format
- Learn about project structure
- Visualize complex relationships

---

## Open Questions & Decisions

### 1. WebSocket vs HTTP Polling?

- **Decision: WebSocket** ✓
- Pros: Real-time, efficient, bidirectional
- Cons: Slightly more complex than HTTP

### 2. Server-Sent Events (SSE) Alternative?

- Simpler than WebSocket but less flexible
- **Stick with WebSocket for bidirectional control**

### 3. Separate Ports for Different Services?

- Port 9001: Remote Script (Live API)
- Port 8765: WebSocket (AST streaming)
- **Decision: Keep separate** ✓ (cleaner separation)

### 4. Authentication/Security?

- Currently localhost-only (no auth needed)
- **For local dev, no auth required** ✓
- Future: Add token-based auth for remote access

### 5. Multiple Project Support?

- Allow viewing multiple projects simultaneously?
- **Start with single project, add multi-project later**

---

## Success Criteria

### Phase 1-2 Success

- [ ] WebSocket server runs without errors
- [ ] Svelte app connects and receives AST
- [ ] Tree structure displays correctly

### Phase 3 Success

- [ ] Real-time updates work smoothly
- [ ] Diffs apply correctly without UI glitches
- [ ] Change highlights appear and fade properly

### Phase 4 Success

- [ ] Search finds nodes accurately
- [ ] Details panel shows complete info
- [ ] Statistics update in real-time

### Phase 5 Success

- [ ] Events from Live appear in UI within 100ms
- [ ] Bi-directional control works reliably
- [ ] Auto-export updates tree automatically

### Overall Success

- [ ] Tree viewer loads in <2 seconds
- [ ] Updates appear within 100ms of change
- [ ] UI remains responsive with 50+ tracks
- [ ] No WebSocket disconnections under normal use
- [ ] User can navigate complex projects efficiently

---

## Notes

- This plan extends the existing AST infrastructure
- Leverages existing node classes and visitor patterns
- Can coexist with previous TODO phases (LSP, write-back)
- Tree viewer is optional - core functionality remains CLI-based
- Perfect for debugging, exploration, and demos
- Can be extended to Max for Live visualizer later

---

## Next Steps

1. **Start with Phase 1a** - Set up WebSocket server
2. **Test incrementally** - Verify each phase works before proceeding
3. **Use Example_Project/** for testing throughout
4. **Document as you go** - Add comments and docstrings
5. **Consider branch strategy** - Use `feature/web-treeviewer` branch
