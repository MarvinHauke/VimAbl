# Project Watcher Implementation Details

## Overview
The project watcher automatically detects when you save Ableton projects (.als files) and starts the WebSocket server for real-time project visualization.

## Key Files
- `src/hammerspoon/project_watcher.lua` - Main watcher logic with broad/narrow modes
- `src/hammerspoon/config.lua` - Watch directory configuration
- `src/hammerspoon/websocket_manager.lua` - WebSocket server lifecycle
- `src/hammerspoon/app_watcher.lua` - Detects Ableton launch/close
- `src/remote_script/commands.py` - XML extraction via gzip

## Two-Mode Architecture

### Broad Mode (Initial State)
**When**: No project active yet, or after switching projects
**What**: Watches base directory + immediate subdirectories (depth 1)
**Why**: Finds any .als file save across multiple projects
**Watchers**: 45-50 typically (depends on number of project folders)

### Narrow Mode (Active Project)
**When**: After detecting first .als save
**What**: Watches only the specific project directory (depth 0)
**Why**: Maximum efficiency - only 1 watcher needed
**Watchers**: 1

**Automatic switching**: After save → 1 second → switches to narrow mode

## Performance Optimizations

### Directory Filtering
Skips these folders during scanning (src/hammerspoon/project_watcher.lua:57):
- `Backup/` - Ableton's automatic backups
- `Ableton Project Info/` - Metadata folder
- `Samples/` - Large sample libraries
- `Recorded*` - Recorded audio files

### Debouncing Strategy
**Problem**: macOS fires multiple events for single save
**Solution**: Two-level debouncing
1. **Time-based**: Ignores saves within 3 seconds (src/hammerspoon/project_watcher.lua:144)
2. **Timer-based**: Cancels pending operations if new save detected (src/hammerspoon/project_watcher.lua:150)

### Timing Configuration
- **Initial delay**: 0.5s after save detection (wait for file flush)
- **Retry delay**: 0.5s between XML export attempts
- **Max retries**: 2 attempts
- **Narrow mode switch**: 1s after successful save
- **Total response time**: ~1.5 seconds from save to running

## Protocol Details

### Command Format
**Colon-delimited**: `COMMAND:param1:param2:param3`

**Example**:
```
EXPORT_XML:/Volumes/ExterneSSD/Ableton Projekte/MyProject/MyProject.als
```

**NOT** JSON or space-separated!

### XML Extraction Process
1. File watcher detects `.als` save → knows exact path
2. Passes path to websocket_manager: `wsManager.start(path)`
3. Sends to Remote Script: `EXPORT_XML:<path>`
4. Python decompresses: `gzip.open(path)` → write to `.vimabl/<name>.xml`
5. Returns: `{"success": true, "xml_path": "...", "project_path": "..."}`

**Key insight**: .als files ARE gzipped XML - no Live API needed!

## Connection Check System

### Exponential Backoff (src/hammerspoon/app_watcher.lua:14-62)
Waits 5 seconds before first check (Remote Script needs time to load)

**Schedule**:
- Attempts 1-3: Every 0.5s (covers 5.0s - 6.5s)
- Attempts 4-6: Every 1.0s (covers 6.5s - 9.5s)
- Attempts 7-10: Every 2.0s (covers 9.5s - 15.5s)

**Result**: Typically connects in 5-6 seconds, max 15.5 seconds

### Benefits
- No wasted early checks (Remote Script not ready before 5s anyway)
- Fast detection once ready (0.5s intervals)
- Graceful backoff for slow loads
- Shows elapsed time and attempt number

## Error Handling

### File System Errors
All operations wrapped in `pcall()` for safety:
- Directory scanning (src/hammerspoon/project_watcher.lua:33)
- File attribute checks (src/hammerspoon/project_watcher.lua:49)
- Watcher creation (src/hammerspoon/project_watcher.lua:126)
- Watcher start (src/hammerspoon/project_watcher.lua:128)

### uv PATH Resolution
Checks in order (src/hammerspoon/websocket_manager.lua:68-73):
1. `~/.local/bin/uv` (default install)
2. `/usr/local/bin/uv` (Homebrew Intel)
3. `/opt/homebrew/bin/uv` (Homebrew ARM)
4. `which uv` (PATH fallback)

### Maximum Watchers
Hard limit: 100 watchers to prevent resource exhaustion
Typically uses: 45-50 in broad mode, 1 in narrow mode

## State Management

### Module Variables (src/hammerspoon/project_watcher.lua:7-13)
```lua
M.watchers = {}              -- Active hs.pathwatcher objects
M.lastDetectedProject = nil  -- Path of last detected .als file
M.lastDetectionTime = 0      -- Timestamp for debouncing
M.activeProjectDir = nil     -- Current project directory (narrow mode)
M.isNarrowMode = false       -- Broad vs narrow mode flag
M.switchTimer = nil          -- Timer for mode switching
M.startTimer = nil           -- Timer for WebSocket start
```

### Mode Transitions
**Broad → Narrow**: After successful .als save and XML export
**Narrow → Broad**: Manual via `M.switchToBroadMode()` or Ableton restart

## Integration Points

### Initialization (app_watcher.lua)
1. Ableton launches → detected by `hs.application.watcher`
2. Wait 5 seconds → start connection polling
3. Wait 2 seconds → start project watcher in broad mode
4. Connection established → show alert

### Save Flow (project_watcher.lua → websocket_manager.lua)
1. `.als` saved → `onFileChanged()` callback fires
2. Check not backup folder → check debounce time
3. Schedule WebSocket start (0.5s delay)
4. Export XML with retries (2 attempts, 0.5s apart)
5. Start WebSocket server with uv
6. Switch to narrow mode (1s delay)

### Cleanup (app_watcher.lua)
1. Ableton quits → detected by application watcher
2. Stop connection timer
3. Stop project watcher
4. Stop WebSocket server

## Future Improvements
- Could add file size check before processing (skip very large files)
- Could cache XML and only re-export if .als modified
- Could add manual "rescan" command to return to broad mode
- Could make max depth and watcher limits configurable
