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

## Phase 1: WebSocket Server Foundation

**Priority: HIGH**
**Dependencies: Existing AST parser (Phase 1a-1b from previous TODO)**
**Goal: Create WebSocket server that can stream AST updates**

### Phase 1a: WebSocket Server Setup

- [ ] Create `src/websocket/` directory structure
  - [ ] Create `src/websocket/__init__.py`
  - [ ] Create `src/websocket/server.py` - Main WebSocket server class
  - [ ] Create `src/websocket/broadcaster.py` - Message broadcasting utility
  - [ ] Create `src/websocket/handlers.py` - WebSocket event handlers
- [ ] Implement `ASTWebSocketServer` class in `server.py`
  - [ ] Use `websockets` library (add to requirements.txt)
  - [ ] Listen on port 8765
  - [ ] Maintain connected clients list
  - [ ] Handle client connections/disconnections
  - [ ] Implement graceful shutdown
- [ ] Implement basic message protocol
  - [ ] Define message types (FULL_AST, DIFF_UPDATE, ERROR, ACK)
  - [ ] Create JSON serialization for AST nodes
  - [ ] Add message validation
- [ ] Add error handling and logging
  - [ ] Connection errors
  - [ ] JSON serialization errors
  - [ ] Client disconnection handling
- [ ] Test WebSocket server
  - [ ] Start server standalone
  - [ ] Connect with test client (websocat or Python script)
  - [ ] Send test AST data
  - [ ] Verify JSON format is correct

### Phase 1b: Integration with Existing AST System

- [ ] Update `src/server/api.py` - Integrate WebSocket broadcasting
  - [ ] Add WebSocket server instance to `ASTServer`
  - [ ] Broadcast full AST on initial client connection
  - [ ] Broadcast diffs when AST changes
  - [ ] Handle multiple connected clients
- [ ] Implement AST change detection
  - [ ] Use existing `DiffVisitor` to compute changes
  - [ ] Trigger broadcast on file watch events
  - [ ] Debounce rapid changes (avoid flooding)
- [ ] Create `src/websocket/serializers.py` - AST to JSON converters
  - [ ] Convert AST nodes to JSON-serializable dicts
  - [ ] Preserve node IDs, types, attributes
  - [ ] Include hash information
  - [ ] Optimize payload size (don't send unchanged subtrees)
- [ ] Test integration
  - [ ] Start AST server with WebSocket enabled
  - [ ] Parse example project
  - [ ] Connect WebSocket client
  - [ ] Verify full AST is received
  - [ ] Modify .als file, verify diff is received

### Phase 1c: Command-Line Interface Updates

- [ ] Update `src/main.py` - Add WebSocket mode
  - [ ] Add `--mode=websocket` option
  - [ ] Add `--ws-port` argument (default 8765)
  - [ ] Start WebSocket server alongside AST server
  - [ ] Enable file watching by default in WebSocket mode
- [ ] Add startup scripts
  - [ ] Create `scripts/start_viewer.sh` - Launch WebSocket server
  - [ ] Create `scripts/start_viewer.py` - Python launcher script
  - [ ] Add instructions to README
- [ ] Test CLI
  - [ ] Run: `python3 -m src.main Example_Project/example.als --mode=websocket`
  - [ ] Verify server starts on port 8765
  - [ ] Check logs for connection status

---

## Phase 2: Svelte Frontend Foundation

**Priority: HIGH**
**Dependencies: Phase 1a (WebSocket server)**
**Goal: Create basic Svelte app that can display AST**

### Phase 2a: SvelteKit Project Setup

- [ ] Create `src/web/frontend/` directory
- [ ] Initialize SvelteKit project
  - [ ] Run: `npm create svelte@latest src/web/frontend`
  - [ ] Choose: Skeleton project, TypeScript, ESLint, Prettier
  - [ ] Install dependencies: `npm install`
- [ ] Configure Tailwind CSS
  - [ ] Install: `npm install -D tailwindcss postcss autoprefixer`
  - [ ] Run: `npx tailwindcss init -p`
  - [ ] Configure `tailwind.config.js` with content paths
  - [ ] Add Tailwind directives to `src/app.css`
- [ ] Set up project structure
  - [ ] Create `src/lib/components/` - Svelte components
  - [ ] Create `src/lib/stores/` - Svelte stores
  - [ ] Create `src/lib/api/` - WebSocket client
  - [ ] Create `src/lib/types/` - TypeScript types
- [ ] Configure dev server
  - [ ] Update `vite.config.ts` for port 5173
  - [ ] Add WebSocket proxy if needed
  - [ ] Configure HMR (Hot Module Replacement)
- [ ] Test setup
  - [ ] Run: `npm run dev`
  - [ ] Open `http://localhost:5173`
  - [ ] Verify default page loads

### Phase 2b: WebSocket Client Implementation

- [ ] Create `src/lib/api/websocket.ts` - WebSocket client
  - [ ] Implement connection to `ws://localhost:8765`
  - [ ] Handle connection lifecycle (open, close, error)
  - [ ] Parse incoming JSON messages
  - [ ] Implement reconnection logic (exponential backoff)
  - [ ] Add TypeScript types for messages
- [ ] Create `src/lib/stores/ast.ts` - AST state management
  - [ ] Use Svelte writable store for AST data
  - [ ] Store full AST tree
  - [ ] Handle FULL_AST messages (replace entire tree)
  - [ ] Handle DIFF_UPDATE messages (patch existing tree)
  - [ ] Add derived stores for statistics (track count, etc.)
- [ ] Create `src/lib/stores/connection.ts` - Connection state
  - [ ] Track WebSocket connection status
  - [ ] Store error messages
  - [ ] Track last update timestamp
- [ ] Create `src/lib/types/ast.ts` - TypeScript AST types
  - [ ] Define interfaces for all node types
  - [ ] Match Python node structure
  - [ ] Add utility types (NodeType enum, etc.)
- [ ] Test WebSocket client
  - [ ] Start WebSocket server
  - [ ] Start Svelte dev server
  - [ ] Verify connection in browser console
  - [ ] Check that AST data is received and stored

### Phase 2c: Basic Tree Component

- [ ] Create `src/lib/components/TreeNode.svelte` - Recursive tree node
  - [ ] Display node type and name
  - [ ] Show/hide children (collapsible)
  - [ ] Display node attributes (hash, index, etc.)
  - [ ] Recursive rendering of child nodes
  - [ ] Add expand/collapse icons
- [ ] Create `src/lib/components/TreeView.svelte` - Root tree container
  - [ ] Render top-level tree structure
  - [ ] Handle empty state (no AST loaded)
  - [ ] Add search/filter input (basic)
  - [ ] Show project metadata (name, track count)
- [ ] Create `src/lib/components/ConnectionStatus.svelte` - Status indicator
  - [ ] Show connection state (connected, disconnected, error)
  - [ ] Display last update time
  - [ ] Show error messages if any
- [ ] Create main page `src/routes/+page.svelte`
  - [ ] Import and use TreeView component
  - [ ] Import and use ConnectionStatus component
  - [ ] Add basic layout (header, main content)
  - [ ] Style with Tailwind CSS
- [ ] Test tree rendering
  - [ ] Load example project in WebSocket server
  - [ ] Open Svelte app in browser
  - [ ] Verify tree structure displays correctly
  - [ ] Test expand/collapse functionality

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

## Phase 5: Remote Script Integration

**Priority: MEDIUM**
**Dependencies: Phase 1, Phase 3**
**Goal: Stream real-time updates from Ableton Live via Remote Script**

### Phase 5a: Remote Script Event Observers

- [ ] Update `src/remote_script/observers.py` - Add AST update observers
  - [ ] Observer for track name changes
  - [ ] Observer for device add/remove
  - [ ] Observer for clip trigger/stop
  - [ ] Observer for parameter value changes
  - [ ] Debounce events to avoid spam
- [ ] Create lightweight event messages
  - [ ] `track_renamed`: {track_index, new_name}
  - [ ] `device_added`: {track_index, device_index, device_name}
  - [ ] `clip_triggered`: {track_index, scene_index}
  - [ ] `parameter_changed`: {track_index, device_index, param_id, value}
- [ ] Send events to WebSocket server
  - [ ] Connect to WebSocket server from Remote Script
  - [ ] Send events as JSON
  - [ ] Handle connection failures gracefully
- [ ] Test event streaming
  - [ ] Rename track in Live
  - [ ] Verify event is sent to WebSocket
  - [ ] Check that Svelte UI updates

### Phase 5b: Bi-Directional Communication (Optional)

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

---

## Phase 6: Advanced Features

**Priority: LOW**
**Dependencies: Phase 4, Phase 5**
**Goal: Add nice-to-have features**

### Phase 6a: Diff History Viewer

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

### Phase 6b: Export & Snapshots

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

### Phase 6c: Theming & Customization

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

## Phase 7: Testing & Documentation

**Priority: HIGH**
**Dependencies: All previous phases**
**Goal: Ensure reliability and usability**

### Phase 7a: Unit Tests

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

### Phase 7b: Integration Tests

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

### Phase 7c: Documentation

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

## Phase 8: Deployment & Distribution

**Priority: LOW**
**Dependencies: Phase 7**
**Goal: Make it easy to run the tree viewer**

### Phase 8a: Production Build

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

### Phase 8b: Standalone Launcher

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

### Phase 8c: Packaging (Optional)

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

---

## Reference Documents

- `SVELTE_TREEVIEWER.md` - Original feature specification
- `REFACTORING_SUMMARY.md` - AST refactoring details
- `README.md` - Project overview
- `src/ast/node.py` - Node class definitions
- `src/ast/visitor.py` - Visitor patterns
