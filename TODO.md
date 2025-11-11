# VimAbl AST Implementation TODO

## Overview

This document combines the AST parser implementation plan with the integration plan for remote_script and Hammerspoon architecture. The goal is to build a rich AST parser for Ableton Live projects and integrate it with the existing Vim-like control system.

---

## Current State Analysis

Your AST architecture is solid with:
- ✅ Well-structured node classes (ProjectNode, TrackNode, DeviceNode, ClipNode, etc.)
- ✅ Visitor pattern implementation (serialization, diffing, searching)
- ✅ Incremental hashing for change detection
- ✅ Server API with query/diff operations

**However**, the parser is minimal - it only extracts `tracks` and `file_refs` (src/parser/ast_builder.py:5-9).

---

## Architecture Vision: `.vimabl/` Folder Integration

### Proposed Project Structure

```
MyProject.als
MyProject/                          # Ableton Project folder
├── Samples/
│   └── ...
├── .vimabl/                        # NEW: VimAbl metadata folder
│   ├── project.xml                 # Decompressed XML for AST parsing
│   ├── ast_cache.json              # Cached AST with hashes
│   ├── ast_info.json               # Project statistics (track count, etc.)
│   └── metadata.json               # VimAbl-specific metadata (bookmarks, marks)
└── ...
```

### Architecture Goals

1. **Auto-export XML** when a project is opened/saved
2. **Store metadata** in a `.vimabl/` folder per project
3. **Query AST** from both remote_script and Hammerspoon
4. **Cache AST** to avoid re-parsing on every operation
5. **Sync state** between Live's runtime state and file-based AST

### Three-Layer Architecture

```
Hammerspoon (UI/Keybindings)
    ↕ port 9001 (existing - Live API commands)
    ↕ port 9002 (new - AST queries)
Remote Script (Live API + XML Export)
    ↕ exports XML to .vimabl/
AST Service (Background Process)
    ↕ watches .vimabl/project.xml
    ↕ provides query API on port 9002
```

---

## Phase 1: Expand the Parser (FOUNDATIONAL - DO THIS FIRST)

**Priority: HIGH**
**Dependencies: None**
**Goal: Make the AST actually contain useful data**

### Phase 1a: Devices & Clips

- [x] Create `src/parser/devices.py` - Extract device information from tracks
  - [x] Parse device names and types (instrument, audio_effect, midi_effect)
  - [x] Extract device parameters (name, value, min, max)
  - [x] Handle device chains (instrument racks, effect racks)
- [x] Create `src/parser/clips.py` - Extract clip information from track clip slots
  - [x] Parse MIDI clips (notes, timing, loop settings)
  - [x] Parse audio clips (file references, warp settings)
  - [x] Extract clip timing (start_time, end_time, loop_start, loop_end)
- [x] Update `src/parser/ast_builder.py` - Integrate devices and clips
  - [x] Call device extraction for each track
  - [x] Call clip extraction for each track
  - [x] Build device subtree for each track
  - [x] Build clip subtree for each track
- [x] Update `src/server/api.py` - Handle new node types in `_build_node_tree()`
  - [x] Convert device dicts to DeviceNode objects
  - [x] Convert clip dicts to ClipNode objects
  - [x] Add device children to track nodes
  - [x] Add clip children to track nodes
- [x] Test with example project
  - [x] Run: `python3 -m src.main Example_Project/example.als --mode=server`
  - [x] Verify devices appear in output
  - [x] Verify clips appear in output
  - [x] Check structure is correct

### Phase 1b: Scenes & Mixer

- [ ] Create `src/parser/scenes.py` - Extract scene information
  - [ ] Parse scene names and indices
  - [ ] Extract scene tempo settings
  - [ ] Link scenes to clip slots
- [ ] Create `src/parser/mixer.py` - Parse mixer settings
  - [ ] Extract volume, pan, mute, solo state
  - [ ] Parse send levels for each track
  - [ ] Extract crossfader assignment
- [ ] Update `src/parser/ast_builder.py` to include scenes and mixer
- [ ] Update `src/server/api.py` to handle SceneNode and MixerNode
- [ ] Test: `python3 -m src.main Example_Project/example.als --mode=info`
  - [ ] Verify scene count is correct
  - [ ] Verify mixer settings are captured

### Phase 1c: Automation

- [ ] Create `src/parser/automation.py` - Extract automation envelopes
  - [ ] Parse automation lanes
  - [ ] Extract automation points (time, value)
  - [ ] Link automation to parameters
- [ ] Update AST to include automation data
- [ ] Test automation extraction with real project

---

## Phase 2: Remote Script Integration (.vimabl/ Foundation)

**Priority: HIGH**
**Dependencies: Phase 1a (needs devices/clips to be useful)**
**Goal: Export XML to `.vimabl/` folder automatically**

### Phase 2a: Document Observer & XML Export

- [ ] Add `ProjectObservers` class to `src/remote_script/observers.py`
  - [ ] Implement `add_document_observer()` for project open/save events
  - [ ] Implement `_on_document_changed()` callback
  - [ ] Get project path from `application.get_document().path`
- [ ] Add `_handle_export_xml()` command to `src/remote_script/commands.py`
  - [ ] Decompress .als file using gzip
  - [ ] Create `.vimabl/` folder in project directory
  - [ ] Write decompressed XML to `.vimabl/project.xml`
  - [ ] Handle errors (no project loaded, permission issues)
- [ ] Register XML export command in `LiveState.py`
- [ ] Test manual XML export
  - [ ] Open project in Ableton Live
  - [ ] Trigger export command via Hammerspoon
  - [ ] Verify `.vimabl/project.xml` is created
  - [ ] Verify XML is valid and parseable

### Phase 2b: Automatic Export on Save

- [ ] Connect document observer to XML export
- [ ] Test automatic export workflow
  - [ ] Make changes to project
  - [ ] Save project (Cmd+S)
  - [ ] Verify `.vimabl/project.xml` is updated
  - [ ] Check timestamp of XML file

---

## Phase 3: AST Service (Background Process)

**Priority: MEDIUM**
**Dependencies: Phase 1a, Phase 2a**
**Goal: Auto-parse XML and cache AST**

### Phase 3a: File Watcher & Auto-Parsing

- [ ] Create `src/ast_service/` directory
- [ ] Create `src/ast_service/service.py` - Main service class
  - [ ] Implement `ASTService` class with file watching
  - [ ] Use existing `FileWatcher` from `src/server/watcher.py`
  - [ ] Watch `.vimabl/project.xml` for changes
  - [ ] Auto-parse on file change
- [ ] Implement caching mechanism
  - [ ] Parse XML → build AST → compute hashes
  - [ ] Save to `.vimabl/ast_cache.json`
  - [ ] Save project info to `.vimabl/ast_info.json`
- [ ] Test file watcher
  - [ ] Start AST service
  - [ ] Modify `.vimabl/project.xml` manually
  - [ ] Verify AST is re-parsed automatically
  - [ ] Check cache files are updated

### Phase 3b: Socket Server for AST Queries

- [ ] Implement socket server in `ASTService` (port 9002)
  - [ ] Listen for JSON commands
  - [ ] Support `find_device` command
  - [ ] Support `get_clips` command
  - [ ] Support `get_project_info` command
  - [ ] Support `query_nodes` with predicates
- [ ] Test socket server
  - [ ] Start AST service
  - [ ] Send test queries via netcat or Python client
  - [ ] Verify responses are correct

### Phase 3c: Service Management

- [ ] Create startup script for AST service
- [ ] Add error handling and logging
- [ ] Implement graceful shutdown
- [ ] Handle multiple projects (track by path)

---

## Phase 4: AST Query Commands in Remote Script

**Priority: MEDIUM**
**Dependencies: Phase 3b (needs AST service API)**
**Goal: Enable remote_script to query AST**

### Phase 4a: AST Client in Remote Script

- [ ] Add AST client to `src/remote_script/commands.py`
  - [ ] Connect to AST service on port 9002
  - [ ] Implement query wrapper functions
- [ ] Add `_handle_find_device_by_name()` command
  - [ ] Query AST service for device by name
  - [ ] Return track index and device index
  - [ ] Handle substring matching
- [ ] Add `_handle_get_all_clips()` command
  - [ ] Query AST for all clips
  - [ ] Return clip locations and timing info
- [ ] Add `_handle_get_automation_targets()` command
  - [ ] Query AST for automated parameters
  - [ ] Useful for "jump to next automated parameter"
- [ ] Register new commands in command handlers
- [ ] Test commands via Hammerspoon
  - [ ] Call find device command
  - [ ] Verify correct device is found
  - [ ] Check performance (should be fast due to cache)

---

## Phase 5: Hammerspoon Integration

**Priority: MEDIUM**
**Dependencies: Phase 4a (needs AST commands)**
**Goal: Create AST-powered keybindings**

### Phase 5a: AST Client Module

- [ ] Create `src/hammerspoon/ast_client.lua`
  - [ ] Implement socket communication to port 9002
  - [ ] Add `findDevice(deviceName)` function
  - [ ] Add `getAllClips()` function
  - [ ] Add `getProjectInfo()` function
  - [ ] Add error handling for connection failures

### Phase 5b: Enhanced Keybindings

- [ ] Add device search keybinding to `src/hammerspoon/keys/navigation.lua`
  - [ ] Show input dialog for device name
  - [ ] Query AST for device
  - [ ] Select track and device via remote_script
- [ ] Add project info display keybinding
  - [ ] Query AST for project stats
  - [ ] Show alert with track/clip/device counts
- [ ] Add clip navigation commands
  - [ ] Jump to next/previous clip
  - [ ] List all clips in current track
- [ ] Test keybindings end-to-end
  - [ ] Open project in Live
  - [ ] Trigger device search
  - [ ] Verify device is selected in Live
  - [ ] Check latency (should be <100ms)

---

## Phase 6: LSP Protocol Layer (FUTURE)

**Priority: LOW**
**Dependencies: Phase 1 complete, Phase 3 complete**
**Goal: Enable LSP client integration (e.g., Neovim, VSCode)**

### Phase 6a: Transport Layer

- [ ] Create `src/lsp/` directory
- [ ] Create `src/lsp/transport.py` - stdio/socket communication
  - [ ] Implement JSON-RPC 2.0 message parsing
  - [ ] Handle Content-Length headers
  - [ ] Support both stdio and TCP socket transports
- [ ] Test transport layer with simple echo server

### Phase 6b: Core LSP Methods

- [ ] Create `src/lsp/handlers.py` - LSP method handlers
- [ ] Implement `initialize` / `initialized`
  - [ ] Return server capabilities
  - [ ] Set up workspace folders
- [ ] Implement `textDocument/didOpen` (treat .als as documents)
  - [ ] Parse .als file on open
  - [ ] Build AST and cache
- [ ] Implement `textDocument/didChange` (for live reloading)
  - [ ] Re-parse on change
  - [ ] Update AST cache
- [ ] Implement `textDocument/hover` (show device/track info)
  - [ ] Map cursor position to AST node
  - [ ] Return markdown documentation
- [ ] Test LSP server with dummy client

### Phase 6c: Custom Ableton Methods

- [ ] Implement `ableton/listTracks`
- [ ] Implement `ableton/findDevice`
- [ ] Implement `ableton/getClipInfo`
- [ ] Implement `ableton/queryNodes`
- [ ] Document custom methods in LSP spec

---

## Phase 7: Write-Back Operations (FUTURE)

**Priority: LOW**
**Dependencies: Phase 1 complete**
**Goal: Edit project files programmatically**

- [ ] Create `src/parser/xml_writer.py` - Serialize AST back to XML
  - [ ] Implement XML generation from AST
  - [ ] Preserve structure and formatting
  - [ ] Handle all node types
- [ ] Implement modification operations
  - [ ] Rename tracks
  - [ ] Rename devices
  - [ ] Modify parameters
  - [ ] Add/remove devices
- [ ] Add validation and safety checks
  - [ ] Validate XML before writing
  - [ ] Create backups before modifying
  - [ ] Verify changes don't corrupt project
- [ ] Test write-back operations
  - [ ] Modify AST programmatically
  - [ ] Write back to .als file
  - [ ] Open in Ableton Live and verify changes

---

## Phase 8: Advanced Features (FUTURE)

**Priority: LOW**
**Dependencies: All previous phases**

### Version Diffing

- [ ] Implement version comparison (compare .als versions)
- [ ] Show what changed between saves
- [ ] Integrate with git for project version control

### Bookmarks and Marks

- [ ] Implement Vim-style marks (ma, 'a)
- [ ] Store in `.vimabl/metadata.json`
- [ ] Add keybindings for setting/jumping to marks

### Custom Metadata

- [ ] Allow storing custom project notes
- [ ] Tag tracks/devices for quick navigation
- [ ] Create named device chains

### AST-based Undo/Redo

- [ ] Track AST changes over time
- [ ] Implement undo/redo based on AST diffs
- [ ] Visualize change history

---

## Data Flow Diagrams

### Project Open Flow

```
User opens project.als in Ableton Live
    ↓
Remote Script: document_observer fires
    ↓
Remote Script: Export XML to .vimabl/project.xml
    ↓
AST Service: Detects new project.xml (watchdog)
    ↓
AST Service: Parse XML → build AST → compute hashes
    ↓
AST Service: Save to .vimabl/ast_cache.json
    ↓
AST Service: Save info to .vimabl/ast_info.json
    ↓
Ready for queries from Hammerspoon
```

### AST Query Flow (Hammerspoon → AST Service)

```
User presses keybinding (e.g., "find device")
    ↓
Hammerspoon: Call ast_client.findDevice("Reverb")
    ↓
AST Service: Search AST for DeviceNode with name="Reverb"
    ↓
AST Service: Return {track_index: 3, device_index: 1}
    ↓
Hammerspoon: Call liveState.selectTrack(3)
    ↓
Remote Script: Execute via Live API
    ↓
Ableton Live: Track 3 selected, device 1 visible
```

### Project Save Flow

```
User saves project (Cmd+S)
    ↓
Remote Script: document_observer fires
    ↓
Remote Script: Export updated XML to .vimabl/project.xml
    ↓
AST Service: Detects project.xml change
    ↓
AST Service: Re-parse AST with new hashes
    ↓
AST Service: Update .vimabl/ast_cache.json
    ↓
AST cache reflects latest project state
```

---

## File Structure Reference

### `.vimabl/project.xml`
- Decompressed XML from .als file
- Updated on every save
- Used by AST parser

### `.vimabl/ast_cache.json`
```json
{
  "node_type": "project",
  "id": "project",
  "hash": "abc123...",
  "children": [
    {
      "node_type": "track",
      "id": "track_0",
      "attributes": {
        "name": "Audio",
        "index": 0,
        "is_muted": false
      },
      "children": [
        {
          "node_type": "device",
          "id": "device_0_0",
          "attributes": {
            "name": "Reverb",
            "device_type": "audio_effect"
          }
        }
      ]
    }
  ]
}
```

### `.vimabl/ast_info.json`
```json
{
  "file": "/path/to/project.als",
  "root_hash": "abc123...",
  "num_tracks": 12,
  "num_devices": 34,
  "num_clips": 56,
  "num_file_refs": 1005,
  "track_names": ["Audio", "MIDI", "Drums", ...],
  "last_updated": "2025-11-11T10:30:00Z"
}
```

### `.vimabl/metadata.json` (Future)
```json
{
  "bookmarks": [
    {"track": 3, "device": 1, "name": "My Reverb Chain"}
  ],
  "custom_mappings": {},
  "vim_marks": {
    "a": {"track": 0, "scene": 0},
    "b": {"track": 5, "scene": 10}
  }
}
```

---

## Architecture Benefits

### 1. Separation of Concerns
- **Remote Script**: Manages Live API, exports XML
- **AST Service**: Parses, caches, queries AST
- **Hammerspoon**: User interface, keybindings

### 2. Performance
- AST cached in JSON, no need to re-parse on every query
- Incremental hashing detects changes quickly
- File watching enables automatic updates

### 3. Flexibility
- AST service can run independently
- Multiple clients can query AST (Hammerspoon, CLI, web UI)
- Easy to add new AST-powered commands

### 4. Extensibility
- `.vimabl/` folder can store arbitrary metadata
- Easy to add version control integration
- Could support plugins/extensions

---

## Open Questions & Decisions Needed

1. **Where should AST service run?**
   - Option A: Standalone Python process (recommended) ✓
   - Option B: Embedded in remote_script (more complex threading)

2. **When to export XML?**
   - On save only? (less I/O, might be stale)
   - On every change? (always fresh, more I/O)
   - On demand? (manual, most control)
   - **Recommendation: On save + on demand**

3. **How to handle multiple projects?**
   - AST service tracks all open projects
   - Use project path as key
   - Clean up closed projects after timeout

4. **Git integration?**
   - Should `.vimabl/` be gitignored? → Yes for cache files
   - Or commit `metadata.json` for shared bookmarks? → Yes, optional

---

## Recommended Execution Order

### Immediate (Week 1-2)
1. ✅ **Phase 1a**: Expand parser with devices and clips
2. ✅ **Test locally**: Verify AST contains useful data

### Short-term (Week 3-4)
3. ✅ **Phase 2a**: Implement XML export in remote_script
4. ✅ **Phase 3a**: Create AST service with file watching

### Medium-term (Week 5-8)
5. ✅ **Phase 3b**: Add socket server to AST service
6. ✅ **Phase 4a**: Add AST query commands to remote_script
7. ✅ **Phase 5**: Integrate with Hammerspoon keybindings

### Long-term (Month 3+)
8. ✅ **Phase 6**: LSP protocol layer (if needed)
9. ✅ **Phase 7**: Write-back operations
10. ✅ **Phase 8**: Advanced features (version diffing, bookmarks)

---

## Notes

- The node classes (DeviceNode, ClipNode, etc.) already exist in `src/ast/node.py`
- The visitor patterns can handle any new node types automatically
- Focus on parsing first (Phase 1) - integration is useless without rich data
- Test incrementally - each phase should be working before moving to the next
- The `.vimabl/` folder concept enables many future features beyond current scope
