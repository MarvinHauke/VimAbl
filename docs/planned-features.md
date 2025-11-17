# Planned Features & Roadmap

This page outlines planned features, upcoming improvements, and the development roadmap for VimAbl.

## Current Status

**Phase Complete:** Phase 5f - UDP/OSC Real-Time Observers ✅
**Overall Progress:** 87.5% (7/8 phases complete)

---

## High Priority Features

### Phase 3: Real-Time Updates & Diff Visualization

**Status:** In Progress
**Dependencies:** WebSocket AST Server (Complete)

#### Phase 3a: Diff Application Logic

- [ ] Enhance AST store with diff patching
  - [ ] Implement `applyDiff(diff)` function
  - [ ] Handle node additions, deletions, modifications
  - [ ] Preserve expand/collapse state during updates
- [ ] Create diff utilities module
  - [ ] Parse diff format from Python server
  - [ ] Map diff paths to tree nodes
  - [ ] Add TypeScript types for diffs

#### Phase 3b: Visual Diff Indicators

- [ ] Add change highlighting to TreeNode component
  - [ ] Green background for new nodes
  - [ ] Yellow background for modified nodes
  - [ ] Red background with strikethrough for removed nodes
  - [ ] Fade out highlights after 5 seconds
- [ ] Create diff legend component
- [ ] Add smooth transition animations

#### Phase 3c: Performance Optimization

- [ ] Implement virtual scrolling for large trees
- [ ] Optimize re-rendering with proper key bindings
- [ ] Add debouncing for rapid updates
- [ ] Test with 50+ track projects

**Estimated Time:** 2-3 weeks

---

### Phase 4: Enhanced UI Features

**Status:** Planned
**Dependencies:** Phase 3

#### Phase 4a: Search & Filter

- [ ] Create search bar component
  - [ ] Text input with debouncing
  - [ ] Search by node name and type
  - [ ] Highlight matching nodes
  - [ ] Show match count
- [ ] Implement search store logic
  - [ ] Full-text search across all nodes
  - [ ] Filter by attributes (muted, armed, etc.)
  - [ ] Support regex patterns
- [ ] Add search navigation
  - [ ] "Next match" (keyboard: n)
  - [ ] "Previous match" (keyboard: N)
  - [ ] Auto-expand tree to show matches

#### Phase 4b: Node Details Panel

- [ ] Create node details component
  - [ ] Show selected node's attributes
  - [ ] Display node hash (SHA)
  - [ ] Show file references
  - [ ] Display parent/child relationships
  - [ ] "Copy JSON" button
- [ ] Add node selection to tree
- [ ] Create split-pane layout (60/40)

#### Phase 4c: Project Statistics Dashboard

- [ ] Create project stats widget
  - [ ] Total track, device, clip counts
  - [ ] File reference count
  - [ ] Last modified timestamp
- [ ] Add real-time statistics updates
- [ ] Create file references list component

**Estimated Time:** 3-4 weeks

---

### Phase 5e: UDP/AST Server Integration

**Status:** Planned
**Priority:** High
**Dependencies:** Phase 5f (Complete)

**Goal:** Connect UDP listener to WebSocket AST server for real-time UI updates

- [ ] Update AST server with event processing
  - [ ] Start UDP listener as async task
  - [ ] Add `process_live_event(event)` method
  - [ ] Map OSC events to AST operations
  - [ ] Batch events (50ms window)
- [ ] Implement incremental AST updates
  - [ ] In-place node updates for renames
  - [ ] Tree structure modifications for add/delete
  - [ ] Minimal diff generation
- [ ] Add XML diff fallback mechanism
  - [ ] Trigger on UDP gap detection
  - [ ] Handle hash mismatches
  - [ ] Log fallback occurrences

**Expected Result:** Real-time UI updates within 100ms when editing in Ableton Live

**Estimated Time:** 1-2 weeks

---

## Medium Priority Features

### More Vim Motions

Expand Vim-style navigation beyond current implementation:

- [ ] `hjkl` navigation (left/down/up/right)
- [ ] Visual mode (`v`) for selecting multiple items
- [ ] Yank (`y`) - Copy selected item
- [ ] Put (`p`) - Paste copied item
- [ ] Change (`c`) - Replace selected item
- [ ] Direct undo (`u`) instead of `za`
- [ ] Redo (`Ctrl+r`)

**Estimated Time:** 2-3 weeks

---

### Advanced Tree Viewer Features

#### Phase 6a: Diff History Viewer

- [ ] Store last N diffs (e.g., 50)
- [ ] Display change history panel
- [ ] Navigate through history
- [ ] Highlight changed nodes from history
- [ ] Optional revert functionality

#### Phase 6b: Export & Snapshots

- [ ] "Export AST as JSON" button
- [ ] Download full AST with timestamp
- [ ] "Load snapshot" functionality
- [ ] Compare current AST with snapshot
- [ ] Show differences in UI

#### Phase 6c: Theming & Customization

- [ ] Dark/light mode toggle (Tailwind)
- [ ] Customizable tree display options
  - [ ] Show/hide node hashes
  - [ ] Show/hide node IDs
  - [ ] Adjust font size
  - [ ] Change color scheme
- [ ] Settings panel with localStorage persistence

**Estimated Time:** 3-4 weeks

---

### Command Palette Overlay

**Status:** Planned
**Priority:** Medium

A Vim-like command palette for quick navigation and control:

- [ ] Overlay UI with fuzzy search
- [ ] Command history
- [ ] Quick track/scene selection
- [ ] Custom command creation
- [ ] Keyboard shortcuts discovery

**Estimated Time:** 2 weeks

---

## Low Priority Features

### Lua Plugin System

**Status:** Planned
**Priority:** Low

Allow users to extend VimAbl with custom Lua plugins:

- [ ] Plugin API specification
- [ ] Plugin loader mechanism
- [ ] Example plugins
- [ ] Plugin documentation
- [ ] Community plugin repository

**Estimated Time:** 4-6 weeks

---

### AI-Powered Features

**Status:** Concept Phase
**Priority:** Low

Intelligent auto-completion and suggestions:

- [ ] Genre-based template suggestions
- [ ] Smart device recommendations
- [ ] Arrangement structure analysis
- [ ] Automated mixing suggestions

**Estimated Time:** TBD (Research phase)

---

### Windows Support

**Status:** Planned
**Priority:** Medium

Port Hammerspoon integration to Windows:

- [ ] AutoHotkey integration (replaces Hammerspoon)
- [ ] Windows-specific keybindings
- [ ] Test on Windows 10/11
- [ ] Windows installation docs

**Estimated Time:** 2-3 weeks

---

## Phase 5 Detailed Roadmap (UDP/OSC)

### Phase 5f: Observer Lifecycle Management ✅ COMPLETE

**Status:** ✅ Complete and Tested
**Date Completed:** 2025-11-12

**What Was Accomplished:**
- LiveState.py integration with UDP sender
- Manual control commands (START/STOP/REFRESH/STATUS)
- Observer status reporting
- Comprehensive documentation
- Manual testing with Ableton Live

**Test Results:**
- End-to-end latency: ~10ms (target was < 100ms)
- CPU usage: ~2% (target was < 5%)
- Packet loss: 0%
- 36+ tracks supported

---

### Phase 5g: OSC Debugging Tools

**Status:** Planned

- [ ] Create `tools/osc_monitor.py`
  - [ ] UDP packet sniffer for port 9002
  - [ ] Pretty-print OSC messages
  - [ ] Color-coded output
- [ ] Create `tools/osc_send.py`
  - [ ] Send test OSC messages
  - [ ] Support all message types
- [ ] Enhanced Remote Script logging

**Estimated Time:** 1 week

---

### Phase 5h: Testing & Validation

**Status:** Planned

- [ ] Unit tests for UDP sender/listener
- [ ] Integration tests (end-to-end)
- [ ] Stress tests (1000+ events)
- [ ] Reliability tests (packet loss simulation)
- [ ] Manual testing checklist completion

**Estimated Time:** 2 weeks

---

### Phase 5i: Bi-Directional Communication (Optional)

**Status:** Planned

Commands from WebSocket/UI to Remote Script:

- [ ] `select_track(index)`
- [ ] `select_device(track_index, device_index)`
- [ ] `toggle_mute(track_index)`
- [ ] `trigger_clip(track_index, scene_index)`
- [ ] Control buttons in Svelte UI
- [ ] Success/error feedback

**Estimated Time:** 1-2 weeks

---

## Phase 9: ZeroMQ Integration (Future)

**Status:** Concept Phase
**Priority:** Low
**Dependencies:** Phase 5 complete and stable

**Goal:** Replace UDP with ZeroMQ for production-grade reliability

**Why Defer?**
- UDP/OSC is simpler and works well for local use
- ZeroMQ requires additional dependencies
- Can migrate later if needed

**Architecture:**
- ZMQ PUB socket in Remote Script
- ZMQ SUB socket in AST server
- Automatic reconnection
- Message queuing during disconnects

**Estimated Time:** 3-4 weeks (when prioritized)

---

## Testing & Documentation Roadmap

### Phase 7a: Unit Tests

- [ ] Set up Vitest framework
- [ ] Write tests for Svelte stores
- [ ] Write tests for utilities
- [ ] Component tests
- [ ] Code coverage reporting

### Phase 7b: Integration Tests

- [ ] Python test suite for WebSocket server
- [ ] End-to-end workflow tests
- [ ] Error scenario tests

### Phase 7c: Documentation

- [ ] Update README with screenshots
- [ ] Create DEVELOPMENT.md
- [ ] Create user guide for TreeViewer
- [ ] Add comprehensive code comments
- [ ] API documentation

**Estimated Time:** 2-3 weeks

---

## Deployment & Distribution

### Phase 8a: Production Build

- [ ] Configure Svelte for production
- [ ] Optimize bundle size
- [ ] Create static file server
- [ ] Combine with WebSocket server

### Phase 8b: Standalone Launcher

- [ ] Unified launcher script
- [ ] Command-line options
- [ ] Auto-open browser
- [ ] Single command: `python3 -m src.main --mode=viewer`

### Phase 8c: Packaging (Optional)

- [ ] Installation script
- [ ] PyInstaller executable
- [ ] macOS .app bundle
- [ ] Distribution testing

**Estimated Time:** 2-3 weeks

---

## Timeline Estimates

### Near Term (Next 1-3 Months)
1. Phase 3: Real-Time Updates (2-3 weeks)
2. Phase 4: Enhanced UI (3-4 weeks)
3. Phase 5e: UDP/AST Integration (1-2 weeks)

### Medium Term (3-6 Months)
1. More Vim Motions (2-3 weeks)
2. Command Palette (2 weeks)
3. Phase 6: Advanced Features (3-4 weeks)
4. Testing & Documentation (2-3 weeks)

### Long Term (6-12 Months)
1. Windows Support (2-3 weeks)
2. Lua Plugin System (4-6 weeks)
3. Production Deployment (2-3 weeks)
4. AI-Powered Features (TBD)

---

## Contributing

Want to help implement these features?

1. Check the [Development Guide](development/extending.md)
2. Pick a feature from the roadmap
3. Open a GitHub issue to discuss approach
4. Submit a pull request

---

## Success Criteria

### Overall Project Success
- [ ] Tree viewer loads in < 2 seconds
- [ ] Updates appear within 100ms of change
- [ ] UI remains responsive with 50+ tracks
- [ ] No WebSocket disconnections under normal use
- [ ] Comprehensive documentation for all features

---

## Notes

- Phases are flexible and may be reordered based on user feedback
- Timeline estimates are approximate and may change
- Some features may be combined or split for efficiency
- Community contributions are welcome and encouraged

---

Last Updated: 2025-11-17
