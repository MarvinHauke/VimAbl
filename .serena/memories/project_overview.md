# Project Overview

## Purpose
Ableton Live LSP provides Vim-like keybindings and LSP-style server functionality for Ableton Live. It enables users to control Live with intuitive keyboard shortcuts powered by a Python Remote Script running inside Ableton and Hammerspoon automation on macOS.

## Key Features
- **Vim-inspired navigation**: Commands like `gg`, `G`, `dd`, `za` and more
- **Context-aware shortcuts**: Different behavior in Arrangement vs Session view
- **Thread-safe Remote Script**: Exposes Live's state via local socket server (port 9001)
- **Modular architecture**: Easy to extend with new commands
- **Auto-recovery**: Monitors and restarts eventtaps automatically

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
└────────┬────────┘
         │ TCP Socket
         ↓
┌─────────────────┐
│ Remote Script   │  Python script running inside Live
│ (LiveState.py)  │  Thread-safe API via schedule_message()
└────────┬────────┘
         │ Live API
         ↓
┌─────────────────┐
│ Ableton Live    │  Tracks, scenes, views, etc.
└─────────────────┘
```

## Communication Protocol
- Hammerspoon sends commands via TCP socket to port 9001
- Commands are processed thread-safely using `schedule_message()`
- Fast path for `GET_VIEW` (no thread switching)
- Expected response time: 20-50ms

## Platform
- **macOS only** (Darwin 24.6.0)
- Requires Ableton Live with Remote Script support
- Uses macOS-specific Hammerspoon for automation
