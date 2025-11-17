# Frequently Asked Questions

## General

### What is VimAbl?

VimAbl brings Vim-style keyboard navigation to Ableton Live, combined with a real-time LSP-like server for project visualization and control.

### Why "VimAbl"?

Vim + Ableton = VimAbl! It combines the efficiency of Vim keybindings with Ableton Live's creative workflow.

### Is VimAbl free?

Yes! VimAbl is open source under the MIT license.

### What versions of Ableton Live are supported?

VimAbl works with any version of Ableton Live that supports Remote Scripts (Live 8+). Tested primarily on Live 11 and 12.

## Installation

### Do I need to install anything inside Ableton?

Yes, you need to install the Remote Script in Ableton's Remote Scripts folder. See [Installation Guide](installation.md).

### Can I use VimAbl without Hammerspoon?

No, Hammerspoon is required for the keyboard shortcuts. However, you can use just the Remote Script API without Hammerspoon.

### Can I use VimAbl on Windows?

The Hammerspoon integration is macOS-only. However, the Remote Script and WebSocket server work on any platform. Windows users could potentially use AutoHotkey instead of Hammerspoon.

## Usage

### Why aren't my commands working?

Common reasons:
1. Ableton Live is not the frontmost application
2. Keys not pressed within 500ms timeout
3. Remote Script not loaded in Ableton
4. Hammerspoon not running

See [Troubleshooting](troubleshooting.md) for solutions.

### Can I customize the keybindings?

Yes! See the [Development Guide](development/extending.md) for how to add or modify keybindings.

### How do I know which view I'm in?

Run: `echo "GET_VIEW" | nc 127.0.0.1 9001`

Or check Ableton's UI - Tab switches between Session and Arrangement views.

### Can I use standard Vim keybindings like hjkl?

Not yet. Currently VimAbl implements `gg`, `G`, `dd`, and `za`. More Vim-style navigation is planned.

## Technical

### What's the latency for commands?

Typically 20-50ms from keypress to execution in Ableton Live.

### How does the real-time observer system work?

The Remote Script monitors Ableton's state via Live API observers and streams events via UDP/OSC to a listener. See [Architecture](architecture/overview.md).

### Why UDP instead of TCP for events?

UDP is fire-and-forget with < 1ms latency, perfect for real-time event streaming. TCP would add acknowledgment overhead.

### What's the CPU usage?

Very low:
- Remote Script: ~2%
- Hammerspoon: < 1%
- UDP Listener: ~1%

### Can I run VimAbl in production/live performance?

Yes! VimAbl is designed for stability and low latency. The auto-recovery features ensure reliability.

## Features

### Does VimAbl work with MIDI controllers?

VimAbl doesn't directly integrate with MIDI controllers, but it works alongside them. The Remote Script uses a separate control surface slot.

### Can I see my project structure in real-time?

Yes! The WebSocket TreeViewer provides live visualization. See [Quick Start](quick-start.md).

### What events does the UDP observer system track?

Track renames, mute/arm state, volume, device parameters, tempo, and more. See [UDP/OSC Observers](user-guide/udp-observers.md).

### Can I add custom commands?

Yes! See the [Development Guide](development/extending.md) for adding new commands.

## Development

### How do I contribute?

Contributions welcome! See the [Development Guide](development/extending.md).

### Can I build plugins for VimAbl?

Plugin system is planned but not yet implemented. Currently you can extend by modifying the source.

### Where's the source code?

[GitHub Repository](https://github.com/yourusername/VimAbl)

### How do I report bugs?

[Open a GitHub Issue](https://github.com/yourusername/VimAbl/issues) with:
- Error messages
- Steps to reproduce
- System information

## Troubleshooting

### I installed everything but nothing works

1. Check Ableton's log for Remote Script errors
2. Verify Hammerspoon is running and has accessibility permissions
3. Test server connection: `echo "GET_VIEW" | nc 127.0.0.1 9001`
4. See [Troubleshooting](troubleshooting.md)

### Commands worked before but stopped

1. Reload Hammerspoon config
2. Restart Ableton Live
3. Check eventtap is running (auto-restarts every 5s)

### The WebSocket server won't start

1. Ensure your project is saved (`.als` file exists)
2. Check port 8765 is available: `lsof -i :8765`
3. Try manual mode: `uv run python -m src.main your_project.als --mode=websocket`

## Future Plans

### What features are planned?

- More Vim motions (hjkl navigation, visual mode)
- Command palette overlay
- AI-powered auto-completion
- Expanded API for third-party extensions

See the [Changelog](changelog.md) for upcoming features.

### Will there be a Windows version?

The Remote Script and WebSocket server work on Windows. Porting the Hammerspoon integration to AutoHotkey is possible but not yet planned.

### Will there be a plugin system?

Yes! A Lua plugin system for custom commands is planned.

## Still Have Questions?

- Check [Troubleshooting](troubleshooting.md)
- Search [GitHub Issues](https://github.com/yourusername/VimAbl/issues)
- Open a new issue with your question
