# Changelog

All notable changes to VimAbl will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Optimized Logging System with Performance Metrics**
  - New streamlined logging architecture:
    - Removed fragile `LogQueue` class and `_log_dispatcher` global
    - Simple module-level functions: `init_logging()`, `drain_log_queue()`, `clear_log_queue()`
    - Tuple-based queueing for faster performance (formatting deferred to main thread)
    - Adaptive queue draining (increases limit when backlog builds)
  - Severity level support: DEBUG, INFO, WARN, ERROR, CRITICAL
  - Real-time performance metrics with <0.1% overhead:
    - `messages_enqueued`, `messages_drained`, `messages_dropped`
    - `peak_queue_size`, `queue_utilization`, `drop_rate`
    - `get_log_stats()` API for programmatic access
    - Automatic stats logging every 5 minutes and on shutdown
  - Comprehensive documentation:
    - New Logging API Reference with all functions documented
    - Expanded Python Remote Script architecture guide
    - Performance impact analysis in Performance Tuning guide
- **ClipSlot Matrix Implementation (Phase 6)**
  - Full ClipSlot grid representation in AST (track × scene matrix)
  - CLIP_SLOT node type with empty and filled slot support
  - Real-time ClipSlot observers for all properties:
    - `has_clip` - Detect clip add/remove
    - `has_stop_button` - Detect stop button enable/disable
    - `playing_status` - Track stopped/playing/triggered states (0/1/2)
    - `color` - Slot color changes
  - Real-time Clip observers when slot has clip:
    - `name` - Detect clip renames
    - `color` - Clip color changes
    - `muted` - Clip mute state
    - `looping` - Loop enable/disable
  - Web UI visualization with icons and states:
    - ▶ Playing (green)
    - ⏸ Triggered/blinking (orange, animated)
    - ■ Stopped (gray)
    - □ Empty slot (light gray)
    - ⊗ No stop button (red)
  - XML parser extracts all clip slots (including empty ones)
  - Backward compatibility maintained with legacy clips array
- Complete MkDocs documentation site
- User guide with navigation and editing commands
- Architecture documentation with Mermaid diagrams
- API reference for OSC protocol and observable properties
- Troubleshooting guide and FAQ
- GitHub Pages deployment workflow with auto-generated documentation

### Changed
- **Logging system refactor:**
  - Replaced `log_simple()` with unified `log()` function taking severity levels
  - Removed deprecated `observer_log()` function
  - All observers now use severity levels (INFO/WARN/ERROR)
  - Updated all Remote Script files: `LiveState.py`, `observers.py`, `cursor_observer.py`, `udp_sender.py`
  - Enhanced `symlink.sh` to show `_Framework/` directory when creating symlink
- Reorganized documentation structure
- Updated mkdocs.yml with comprehensive navigation
- Enhanced AST updater with ClipSlot event handlers
- Simplified web UI visual effects - removed add/modify/delete animations
- Unified selection highlighting to blue for both tracks and clip slots
- Immediate DOM updates (no animation delays) for better performance

### Fixed
- XPath selector bug causing double-counting of clip slots (`.//ClipSlot` → `./ClipSlot`)
- Clip slot selection now uses consistent blue highlight matching track selection
- Remote Script initialization crash due to missed `observer_log()` calls in `ObserverManager.__init__()`

### Performance
- **10-20% faster logging** due to tuple-based queueing
- **Better burst handling** with larger queue (2000 vs 1000) and adaptive draining
- **Faster level filtering** using set lookup instead of if/else chains
- **Reduced global lookups** with cached queue references
- **Metrics tracking overhead: <0.1% CPU** (negligible impact)

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
