# Changelog

All notable changes to VimAbl will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-11-25

### Added
- **Real-Time AST Synchronization (Phase 5e)**
  - Integration of UDP listener with AST Server (`src/server/api.py`)
  - Processing of real-time OSC events (`process_live_event`)
  - Incremental AST updates (in-place modification for renames/state changes)
  - Immediate broadcasting of diffs to WebSocket clients
  - Fallback mechanism: Automatic XML reload when UDP event gaps > 5 are detected
- **ClipSlot Matrix Implementation (Phase 6)**
  - Full ClipSlot grid representation in AST (track × scene matrix)
  - `CLIP_SLOT` node type with empty and filled slot support
  - Real-time ClipSlot observers for all properties:
    - `has_clip`, `has_stop_button`, `playing_status`, `color`
  - Real-time Clip observers: `name`, `color`, `muted`, `looping`
  - Web UI visualization with icons and states:
    - ▶ Playing (green)
    - ⏸ Triggered/blinking (orange, animated)
    - ■ Stopped (gray)
    - □ Empty slot (light gray)
    - ⊗ No stop button (red)
- **UDP Listener Queue Architecture (Phase 5j)**
  - Non-blocking event processing with `asyncio.Queue` (maxsize=1000)
  - Decoupled UDP packet reception from WebSocket broadcasting
  - Separate event processor task for concurrent handling
  - Eliminates packet loss during rapid event bursts
  - Queue statistics tracking: `queue_size`, `queue_max`
- **_Framework.Task Integration in Remote Script**
  - Migrated polling logic from `update_display()` to Task system
  - Three recurring tasks scheduled at ~60Hz:
    - Observer manager polling (debounce/batching)
    - Cursor observer updates (`highlighted_clip_slot`)
    - Performance stats logging (every 5 minutes)
  - Fallback to legacy polling if Task setup fails
- **Optimized Logging System with Performance Metrics**
  - Streamlined logging architecture with module-level functions
  - Tuple-based queueing for faster performance
  - Adaptive queue draining
  - Real-time performance metrics (<0.1% overhead)
  - New Logging API Reference and documentation

### Changed
- **Node ID Format Standardization**
  - Client-side ID generation matches server format
  - Removed timestamp suffixes from dynamically created nodes
  - ClipSlot IDs: `clip_slot_2_3`
  - Device IDs: `device_2_1`
- **Logging system refactor:**
  - Replaced `log_simple()` with unified `log()` function
  - All observers now use severity levels (INFO/WARN/ERROR)
- **Documentation Updates**:
  - Reorganized documentation structure
  - Updated mkdocs.yml with comprehensive navigation
  - Enhanced AST updater with ClipSlot event handlers
- **Web UI Improvements**:
  - Simplified visual effects (removed add/modify/delete animations)
  - Unified selection highlighting to blue
  - Immediate DOM updates for better performance

### Fixed
- **Scene Insertion Position**: Scenes now inserted after tracks in AST structure
- **UDP Packet Loss**: Fixed gap detection warnings during rapid bursts using queue architecture
- **_Framework.Task Import Error**: Fixed incorrect import path
- **XPath Selector Bug**: Fixed double-counting of clip slots
- **Clip Slot Selection**: Consistent blue highlight matching track selection

### Performance
- **UDP Listener**: Zero packet loss with asyncio.Queue architecture
- **Remote Script**: `update_display()` reduced to 7 lines via Task delegation
- **Logging**: 10-20% faster with tuple-based queueing
- **Metrics**: <0.1% CPU overhead for tracking

## [0.3.0] - 2025-11-16


### Added
- Session View cursor tracking
- Real-time UI highlighting for selected scene
- Track color support in TreeViewer
- Track naming in TreeViewer
- Flashing indicators for last changes in web UI

### Changed
- Enhanced cursor tracking architecture
- Improved TreeViewer visual feedback

## [0.2.0] - 2025-11-12

### Added
- UDP/OSC Real-Time Observer System (Phase 5f)
  - TrackObserver for track property monitoring
  - DeviceObserver for device parameter monitoring
  - TransportObserver for playback state and tempo
- UDP Listener Bridge for event processing
- OSC protocol specification
- Debouncing for high-frequency events (volume, device parameters)
- Manual observer controls (START/STOP/REFRESH/STATUS)
- Comprehensive testing suite for UDP/OSC integration

### Performance
- End-to-end latency: ~10ms (target was < 100ms)
- UDP send time: ~0.5ms (target was < 1ms)
- CPU usage: ~2% Remote Script, ~1% UDP Listener
- Zero packet loss on localhost
- Support for 36+ tracks tested

### Documentation
- OSC Protocol documentation
- Observer reference guide
- Manual testing procedures
- Integration test suite

## [0.1.0] - 2025-11-10

### Added
- Initial VimAbl implementation
- Python Remote Script (LiveState.py)
  - Thread-safe command API via TCP socket (port 9001)
  - View state monitoring (Session/Arrangement)
  - Fast-path for read-only operations
- Hammerspoon Integration
  - Vim-style navigation (`gg`, `G`)
  - Editing commands (`dd`, `za`)
  - Browser toggle (`Ctrl + -`)
  - Application watcher for auto-enable/disable
  - Auto-recovery for eventtaps (every 5 seconds)
- WebSocket AST Server (port 8765)
  - .als file parsing to AST
  - Real-time project visualization
  - WebSocket streaming to UI
- Svelte Web UI (TreeViewer)
  - Interactive tree view of project structure
  - Real-time updates via WebSocket
  - Track, device, and sample visualization

### Commands
- `GET_VIEW` - Get current view (session/arrangement)
- `GET_STATE` - Get full Live state
- `SELECT_FIRST_SCENE` - Jump to first scene
- `SELECT_LAST_SCENE` - Jump to last scene
- `SELECT_FIRST_TRACK` - Jump to first track
- `SELECT_LAST_TRACK` - Jump to last track

### Documentation
- Initial README with installation instructions
- Architecture overview
- Quick start guide
- Development setup instructions

## Version History

### [0.3.0] - Session View Cursor Tracking
Major UI improvements for TreeViewer with real-time cursor tracking and visual feedback.

### [0.2.0] - UDP/OSC Real-Time Observers
Major feature release adding real-time event streaming with exceptional performance.

### [0.1.0] - Initial Release
First public release with core Vim-style navigation and WebSocket visualization.

---

## Release Notes Format

Each release includes:
- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security fixes
- **Performance** - Performance improvements

---

[Unreleased]: https://github.com/yourusername/VimAbl/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/yourusername/VimAbl/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/yourusername/VimAbl/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourusername/VimAbl/releases/tag/v0.1.0
