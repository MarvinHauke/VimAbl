# VimAbl

<div align="center">

**Vim-like keyboard control for Ableton Live with real-time project visualization**

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://marvinhauke.github.io/VimAbl/)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![Ableton Live](https://img.shields.io/badge/Ableton%20Live-10%2B-orange)](https://www.ableton.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Documentation](https://marvinhauke.github.io/VimAbl/) • [Architecture](#-architecture)

<img src="docs/assets/demo.gif" alt="VimAbl Demo" width="800"/>

</div>

---

## 🎯 What is VimAbl?

VimAbl brings the efficiency of Vim-style keyboard navigation to Ableton Live, combined with an LSP-like server architecture for real-time project visualization and control. Navigate tracks, scenes, and devices with familiar commands like `gg`, `G`, and `dd`, while monitoring your project structure through a live web interface.

## ✨ Features

### 🎹 Vim-Inspired Navigation
- **Session View**: `gg` (first scene), `G` (last scene), `za` (undo), `dd` (delete)
- **Arrangement View**: `gg` (first track), `G` (last track), auto-scrolling
- **Context-aware**: Different behavior based on current view
- **Auto-recovery**: Eventtaps restart automatically if disabled

### ⚡ Real-Time Synchronization
- **UDP/OSC Observers**: Stream Live events with < 10ms latency
- **WebSocket AST Server**: Live project visualization on port 8765
- **Visual Change Indicators**:
  - 🟢 Green: Nodes added (1 second slide-in)
  - 🟡 Yellow: Nodes modified (1 second pulse)
  - 🔴 Red: Nodes removed (1 second fade-out)
  - 🔵 Blue flash: Attribute changes (600ms)

### 🌲 Web TreeViewer
- **Interactive project browser**: Explore tracks, devices, clips, and samples
- **Real-time updates**: See changes as you work in Live (< 100ms latency)
- **Cursor tracking**: Highlights selected track/clip slot
- **Track color coding**: Displays Ableton's color palette
- **Dark mode support**: Seamless theme switching

### 🔒 Thread-Safe Architecture
- **Remote Script**: Python server running inside Live (port 9001)
- **Hammerspoon Integration**: Lua automation for macOS keyboard shortcuts
- **Modular Design**: Easy to extend with new commands

## 🚀 Quick Start

### Prerequisites

- **macOS** (Hammerspoon requirement)
- **Ableton Live** 10+ with Remote Script support
- **Hammerspoon** - [Download](https://www.hammerspoon.org/)
- **Python 3.11+** - For external tools
- **uv** - Python package manager ([Install](https://github.com/astral-sh/uv))

### Installation

1. **Install uv**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and setup**:
   ```bash
   git clone https://github.com/MarvinHauke/VimAbl.git
   cd VimAbl
   uv sync
   ```

3. **Install Remote Script**:
   ```bash
   ln -s "$(pwd)/src/remote_script" ~/Music/Ableton/User\ Library/Remote\ Scripts/LiveState
   ```

4. **Enable in Ableton**:
   - Open Live Preferences → Link/Tempo/MIDI
   - Select **LiveState** as Control Surface
   - Restart Ableton Live

5. **Install Hammerspoon scripts**:
   ```bash
   mkdir -p ~/.hammerspoon/keys
   ln -s "$(pwd)/src/hammerspoon/ableton.lua" ~/.hammerspoon/
   # ... (see full installation in docs)
   ```

6. **Add to Hammerspoon config** (`~/.hammerspoon/init.lua`):
   ```lua
   require("ableton")
   ```

7. **Reload Hammerspoon** (Menu bar → Reload Config)

### Verify Installation

```bash
# Check Remote Script is loaded
tail -f ~/Library/Preferences/Ableton/Live\ */Log.txt
# Look for: "Live State Remote Script initialized"

# Test server connection
echo "GET_VIEW" | nc 127.0.0.1 9001
# Should return: {"view": "session"} or {"view": "arrangement"}
```

## 📖 Usage

### Keyboard Shortcuts

| Key | Session View | Arrangement View |
|-----|--------------|------------------|
| `gg` | Select first scene | Select first track |
| `G` | Select last scene | Select last track |
| `za` | Undo | Undo |
| `dd` (double-tap) | Delete | Delete |
| `ctrl + -` | Toggle browser | Toggle browser |

### Web TreeViewer

**Automatic Mode** (with Hammerspoon):
1. Save your Ableton project
2. Launch Ableton Live
3. Server starts automatically after ~5 seconds
4. Open http://localhost:8765 in your browser

**Manual Mode**:
```bash
# Terminal 1: Start WebSocket server
uv run python -m src.main path/to/project.als --mode=websocket

# Terminal 2: Start Svelte dev server (for development)
cd src/web/frontend
npm install
npm run dev

# Open http://localhost:5173 in browser
```

**Manual Controls** (Hammerspoon):
- `Cmd+Shift+W`: Toggle WebSocket server
- `Cmd+Shift+R`: Restart server
- `Cmd+Shift+I`: Show server status

## 🏗️ Architecture

```
┌─────────────────────┐
│   User Input        │  Keyboard shortcuts
│   (Hammerspoon)     │
└──────────┬──────────┘
           │ TCP (port 9001)
           ↓
┌─────────────────────┐
│   Remote Script     │  Python running inside Live
│   (LiveState.py)    │  Thread-safe API
└──────────┬──────────┘
           │ Live API
           ↓
┌─────────────────────┐      ┌──────────────────┐
│   Ableton Live      │─────→│  UDP Listener    │
│                     │      │  (port 9002)     │
└─────────────────────┘      └────────┬─────────┘
                                      │ OSC Events
                                      ↓
                             ┌──────────────────┐
                             │  WebSocket       │
                             │  Server          │
                             │  (port 8765)     │
                             └────────┬─────────┘
                                      │ JSON/WebSocket
                                      ↓
                             ┌──────────────────┐
                             │  Svelte Web UI   │
                             │  (TreeViewer)    │
                             └──────────────────┘
```

### Key Components

1. **Remote Script** (`src/remote_script/LiveState.py`)
   - Runs inside Ableton Live
   - Exposes thread-safe TCP server (port 9001)
   - Sends real-time UDP/OSC events (port 9002)

2. **Hammerspoon Scripts** (`src/hammerspoon/`)
   - Lua automation for macOS
   - Keyboard shortcut handlers
   - Auto-detects Live open/close
   - Manages WebSocket server lifecycle

3. **UDP Listener** (`src/udp_listener/`)
   - Receives OSC events from Live
   - Parses `/live/seq` wrapped messages
   - Gap detection for reliability

4. **WebSocket Server** (`src/server/`)
   - Parses `.als` XML files
   - Builds Abstract Syntax Tree (AST)
   - Broadcasts incremental diffs
   - Handles real-time event routing

5. **Svelte Frontend** (`src/web/frontend/`)
   - Real-time tree visualization
   - Cursor tracking and highlighting
   - Visual change indicators
   - Dark mode support

## 📊 Performance Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| End-to-end latency (UDP → UI) | < 150ms | ~100ms | ✅ 33% better |
| UDP send time | < 1ms | ~0.5ms | ✅ 2x better |
| Flash animation duration | 500-1000ms | 600ms | ✅ |
| High-freq throttle interval | 50-200ms | 100ms | ✅ |
| Memory overhead | < 10MB | ~5MB | ✅ 2x better |
| CPU usage (Remote Script) | < 5% | ~2% | ✅ |
| Packet loss | < 0.1% | 0% | ✅ Perfect |

## 📚 Documentation

**Full documentation available at: [https://marvinhauke.github.io/VimAbl/](https://marvinhauke.github.io/VimAbl/)**

- [Installation Guide](https://marvinhauke.github.io/VimAbl/installation/) - Complete setup instructions
- [Quick Start](https://marvinhauke.github.io/VimAbl/quick-start/) - Get running in 5 minutes
- [User Guide](https://marvinhauke.github.io/VimAbl/user-guide/overview/) - Navigation, editing, keybindings
- [Web TreeViewer](https://marvinhauke.github.io/VimAbl/user-guide/web-treeviewer/) - Real-time visualization guide
- [Architecture](https://marvinhauke.github.io/VimAbl/architecture/overview/) - System design deep dive
- [WebSocket AST](https://marvinhauke.github.io/VimAbl/architecture/websocket-ast/) - Architecture details
- [API Reference](https://marvinhauke.github.io/VimAbl/api-reference/commands/) - Commands and protocols
- [Troubleshooting](https://marvinhauke.github.io/VimAbl/troubleshooting/) - Common issues
- [Development Guide](https://marvinhauke.github.io/VimAbl/development/extending/) - Contributing

## 🔧 Development

### Project Structure

```
VimAbl/
├── src/
│   ├── remote_script/          # Python Remote Script (runs inside Live)
│   │   ├── __init__.py
│   │   └── LiveState.py        # Main controller with socket server
│   ├── hammerspoon/            # Lua automation scripts
│   │   ├── ableton.lua         # Entry point
│   │   ├── live_state.lua      # Server communication
│   │   ├── app_watcher.lua     # Detect Live open/close
│   │   └── keys/               # Keybinding modules
│   ├── server/                 # AST server and WebSocket
│   │   ├── api.py              # ASTServer with event handlers
│   │   └── websocket.py        # WebSocket server
│   ├── udp_listener/           # UDP/OSC event receiver
│   │   └── listener.py
│   └── web/frontend/           # Svelte web UI
│       ├── src/lib/stores/     # State management
│       └── src/routes/         # Pages
├── docs/                       # MkDocs documentation
├── tools/                      # Build and extraction scripts
└── tests/                      # Test suite
```

### Adding New Commands

1. **Add handler in Remote Script** (`src/remote_script/LiveState.py`):
   ```python
   def _handle_your_command(self, params=None):
       """Handle YOUR_COMMAND"""
       # Your logic using self.song()
       return {"success": True, "data": "..."}
   ```

2. **Register in `_register_commands()`**:
   ```python
   "YOUR_COMMAND": self._handle_your_command,
   ```

3. **Add wrapper in Lua** (`src/hammerspoon/live_state.lua`):
   ```lua
   function M.yourCommand()
       return sendCommand("YOUR_COMMAND")
   end
   ```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Run specific test file
uv run pytest tests/test_ast_builder.py
```

### Building Documentation Locally

```bash
# Install docs dependencies
uv pip install mkdocs mkdocs-material mkdocs-git-revision-date-localized-plugin

# Serve docs locally
mkdocs serve

# Open http://127.0.0.1:8000
```

## 🛠️ Troubleshooting

### Remote Script not loading
- Check folder is named exactly `LiveState`
- View `~/Library/Preferences/Ableton/Live */Log.txt` for errors
- Verify Python syntax: `python3 -m py_compile src/remote_script/LiveState.py`

### Shortcuts stop working
- **Fixed!** Eventtaps auto-restart every 5 seconds if disabled
- Check Hammerspoon console for: `"WARNING - eventtap was disabled, restarting..."`

### Server connection fails
```bash
# Check if server is running
lsof -i :9001

# Test manually
echo "GET_STATE" | nc 127.0.0.1 9001
```

### Web UI not updating
1. Check Remote Script is running (see Ableton preferences)
2. Verify UDP listener: `python3 tools/test_udp_manual.py`
3. Check browser console (F12) for logs
4. Save project to trigger XML reload

More solutions in the [Troubleshooting Guide](https://marvinhauke.github.io/VimAbl/troubleshooting/).

## 🗺️ Roadmap

### Current (v0.3.0)
- ✅ Basic Vim navigation (`gg`, `G`, `dd`, `za`)
- ✅ UDP/OSC real-time observers
- ✅ WebSocket AST visualization
- ✅ Visual change indicators (green/yellow/red)
- ✅ Cursor tracking with auto-scroll
- ✅ Track color display

### Planned Features
- 🔄 Bi-directional control (UI → Live)
- 🎛️ Device parameter editing via UI
- 🎬 Clip launching from TreeViewer
- 🔍 Search and filter nodes
- ⌨️ More Vim motions (`hjkl`, visual mode)
- 🎨 Command palette overlay
- 🧩 Lua plugin system

See [Planned Features](https://marvinhauke.github.io/VimAbl/planned-features/) for full roadmap.

## 🤝 Contributing

Contributions are welcome! VimAbl is in active development with symlink-based workflow for rapid iteration.

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test thoroughly**: `uv run pytest`
5. **Commit**: `git commit -m 'Add amazing feature'`
6. **Push**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/VimAbl.git
cd VimAbl

# Create development environment
uv sync --all-extras

# Install as editable with symlinks
ln -s "$(pwd)/src/remote_script" ~/Music/Ableton/User\ Library/Remote\ Scripts/LiveState
ln -s "$(pwd)/src/hammerspoon/"*.lua ~/.hammerspoon/
```

See [Development Guide](https://marvinhauke.github.io/VimAbl/development/extending/) for more details.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ableton Live** - For the powerful music creation platform
- **Hammerspoon** - For making macOS automation accessible
- **Vim** - For inspiring the navigation paradigm
- **LSP** - For the server architecture pattern
- **Svelte** - For the reactive web framework

## 📞 Support

- **Documentation**: [https://marvinhauke.github.io/VimAbl/](https://marvinhauke.github.io/VimAbl/)
- **Issues**: [GitHub Issues](https://github.com/MarvinHauke/VimAbl/issues)
- **Discussions**: [GitHub Discussions](https://github.com/MarvinHauke/VimAbl/discussions)

---

<div align="center">

**Made with ❤️ for Ableton Live users who love keyboard shortcuts**

[⬆ Back to top](#vimabl)

</div>
