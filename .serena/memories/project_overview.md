# Project Overview

## Purpose
Ableton Live LSP provides Vim-like keybindings and LSP-style server functionality for Ableton Live. It enables users to control Live with intuitive keyboard shortcuts powered by a Python Remote Script running inside Ableton and Hammerspoon automation on macOS.

## Key Features
- **Vim-inspired navigation**: Commands like `gg`, `G`, `dd`, `za` and more
- **Context-aware shortcuts**: Different behavior in Arrangement vs Session view
- **Thread-safe Remote Script**: Exposes Live's state via local socket server (port 9001)
- **Modular architecture**: Easy to extend with new commands
- **Auto-recovery**: Monitors and restarts eventtaps automatically
- **Smart project watcher**: Auto-detects .als file saves and starts WebSocket server
- **XML extraction**: Decompresses .als files to XML for AST analysis
- **Web tree viewer**: Real-time WebSocket server (port 8765) for project visualization
- **Intelligent connection polling**: Exponential backoff for fast startup detection

## Tech Stack

### Languages
- **Python**: Remote Script that runs inside Ableton Live (Python 3.11/3.13 compatible)
- **Lua**: Hammerspoon automation scripts for keyboard shortcuts

### Key Technologies
- **Ableton Live API**: Python API for controlling Live (_Framework.ControlSurface)
- **Hammerspoon**: macOS automation tool for keyboard shortcuts and app monitoring
- **Socket Communication**: TCP socket server on port 9001 for Python-Lua communication
- **Threading**: Thread-safe command execution with locks and event synchronization

## Architecture

```
┌─────────────────┐
│ Hammerspoon     │  Lua automation, keyboard shortcuts
│ (Port: 9001)    │  Auto-detects Live open/close
│                 │  Project file watcher (.als saves)
└────────┬────────┘
         │ TCP Socket (colon-delimited protocol)
         ↓
┌─────────────────┐
│ Remote Script   │  Python script running inside Live
│ (LiveState.py)  │  Thread-safe API via schedule_message()
│                 │  XML extraction from .als files
│                 │  UDP sender for real-time events (Port 9002)
└────────┬────────┘
         │ Live API
         ↓
┌─────────────────┐
│ Ableton Live    │  Tracks, scenes, views, etc.
│                 │  Live API observers for changes
└────────┬────────┘
         │
         ├─ .als file save (gzipped XML) ─────────┐
         │                                         ↓
         └─ UDP/OSC events ────────┐   ┌──────────────────┐
                                   ↓   │ WebSocket Server │
                        ┌──────────────┤ (Port 8765)      │
                        │ UDP Listener │ Real-time AST    │
                        │ (Port 9002)  │ streaming to UI  │
                        │ Deduplicates │ Parses XML       │
                        │ Forwards to  │ Computes diffs   │
                        │ AST Server   │ Broadcasts       │
                        └──────────────┴──────────────────┘
                                   ↓
                        ┌──────────────────┐
                        │ Svelte TreeViewer│
                        │ Real-time UI     │
                        │ Visual diffs     │
                        └──────────────────┘
```


## Communication Protocol

### Remote Script Socket (Port 9001)
- Hammerspoon sends commands via TCP socket to port 9001
- **Protocol format**: Colon-delimited (e.g., `COMMAND:param1:param2`)
- Commands are processed thread-safely using `schedule_message()`
- Fast path for `GET_VIEW` (no thread switching)
- Expected response time: 20-50ms
- Example commands:
  - `GET_STATE` - Get current view and playback state
  - `EXPORT_XML:/path/to/project.als` - Extract XML from .als file
  - `JUMP_TO_FIRST` - Navigate to first track/scene

### UDP/OSC Real-Time Observer (Port 9002) ✅ PRODUCTION
- **Status**: Fully implemented and tested with Ableton Live (Phase 5f complete)
- UDP packets with OSC schema for real-time events from Live
- **Ultra-low latency**: < 10ms end-to-end (measured in production)
- Non-blocking - Remote Script never waits for acknowledgment
- **Performance**: < 2% CPU usage with 36 tracks, 0% packet loss on localhost
- Events wrapped with sequence numbers for ordering and deduplication
- Debouncing for rapid parameter changes:
  - Volume/device parameters: 50ms
  - Tempo changes: 100ms
  - Structural changes (name, mute, arm): 0ms (immediate)
- Located at: `src/remote_script/udp_sender.py` and `src/udp_listener/`
- Protocol documented in: `docs/OSC_PROTOCOL.md`
- Full observer list: `docs/ESTABLISHED_OBSERVERS.md`

**Active Observers:**
- **TrackObserver**: name, mute, arm, volume, device add/remove (✅ verified)
- **DeviceObserver**: parameters (first 8 per device) (✅ verified)
- **TransportObserver**: play/stop, tempo (✅ verified)

**Example events:**
  - `/live/track/renamed [track_idx, name]`
  - `/live/track/mute [track_idx, bool]`
  - `/live/track/volume [track_idx, float]` (debounced 50ms)
  - `/live/device/added [track_idx, device_idx, name]`
  - `/live/device/param [track_idx, device_idx, param_idx, value]` (debounced 50ms)
  - `/live/transport/tempo [float_bpm]` (debounced 100ms)

**Manual Controls (via TCP port 9001):**
  - `START_OBSERVERS` - Enable real-time updates
  - `STOP_OBSERVERS` - Disable (save CPU)
  - `REFRESH_OBSERVERS` - Refresh observer list
  - `GET_OBSERVER_STATUS` - Get statistics

**Future**: Fallback to XML diff if UDP packets are lost (gap > 10 messages) - Phase 5e

### WebSocket Server (Port 8765)
- Started automatically when .als file is saved
- Serves project AST as JSON over WebSocket
- Uses `uv` to run Python server
- Located at: `~/Development/python/VimAbl/src/server`
- XML files stored in: `<project>/.vimabl/<name>.xml`

## Project Watcher System

### Smart File Watching
- **Broad mode**: Scans configured directories (depth 1) for any .als saves
- **Narrow mode**: After first save, watches only active project directory
- **Optimizations**:
  - Skips backup folders (Backup/, Ableton Project Info/, Samples/, Recorded*)
  - 3-second debouncing to prevent duplicate triggers
  - 0.5-second delay after save before processing
  - Exponential backoff for connection checks (starts at 5s)

### Configuration
- Watch directories defined in `src/hammerspoon/config.lua`
- Default paths:
  - `~/Music`
  - `/Volumes/ExterneSSD/Ableton Projekte`

### XML Extraction
- .als files are gzipped XML - no Live API needed!
- Direct decompression using Python's `gzip` module
- Instant extraction (no waiting for Live API)
- Stored in `.vimabl/<project_name>.xml`

## Platform
- **macOS only** (Darwin 24.6.0)
- Requires Ableton Live with Remote Script support
- Uses macOS-specific Hammerspoon for automation
- Requires `uv` for WebSocket server (installed at `~/.local/bin/uv`)
