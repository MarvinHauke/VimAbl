# Ableton Live LSP

Vim-like keybindings and LSP-style server functionality for Ableton Live. Control Live with intuitive keyboard shortcuts powered by a Python Remote Script and Hammerspoon automation.

## Features

- **Vim-inspired navigation**: `gg`, `G`, `dd`, `za` and more
- **Context-aware shortcuts**: Different behavior in Arrangement vs Session view
- **Thread-safe Remote Script**: Exposes Live's state via local socket server (port 9001)
- **UDP/OSC Real-Time Observers** ⭐ NEW!: Streams Live events with < 10ms latency (port 9002)
- **Web TreeViewer**: Real-time project visualization via WebSocket (port 8765)
- **Modular architecture**: Easy to extend with new commands
- **Auto-recovery**: Monitors and restarts eventtaps automatically

📚 **[Complete Documentation](docs/README.md)** | 🎯 **[Observer Reference](docs/ESTABLISHED_OBSERVERS.md)**

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

## Installation

### Prerequisites

- **Ableton Live** (any version with Remote Script support)
- **Hammerspoon** - macOS automation tool ([Download](https://www.hammerspoon.org/))
- **Python 3.11+** - For external tools (AST parser, WebSocket server)
- **uv** - Python package manager ([Install](https://github.com/astral-sh/uv))

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with Homebrew:

```bash
brew install uv
```

### 2. Install Project Dependencies

```bash
# Sync all dependencies (creates .venv automatically)
uv sync

# Or with dev dependencies
uv sync --all-extras
```

### 3. Activate Virtual Environment

**Option 1: Use direnv (recommended)**

If you have [direnv](https://direnv.net/) installed:

```bash
# Allow direnv to load .envrc
direnv allow

# Now it auto-activates when you cd into the directory!
cd /path/to/VimAbl  # Environment auto-loads
```

**Option 2: Use uv run** (recommended if no direnv)

```bash
uv run python -m src.main --help
```

**Option 3: Activate manually**

```bash
source .venv/bin/activate
python -m src.main --help
```

### 4. Install Remote Script

Create a symlink to the remote script in Ableton's Remote Scripts folder (recommended for development):

```bash
# macOS
ln -s "$(pwd)/src/remote_script" ~/Music/Ableton/User\ Library/Remote\ Scripts/LiveState

# Windows
mklink /D "%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\LiveState" "%CD%\src\remote_script"
```

**Alternative (production):** Copy instead of symlinking:
```bash
cp -r src/remote_script ~/Music/Ableton/User\ Library/Remote\ Scripts/LiveState
```

### 5. Enable Remote Script in Ableton

1. Open Ableton Live **Preferences**
2. Go to **Link/Tempo/MIDI** tab
3. Under **Control Surface**, select **LiveState** in an empty slot
4. Set Input/Output to **None**
5. **Restart Ableton Live**

### 6. Install Hammerspoon Scripts

Create symlinks for development (recommended):

```bash
# Create directory structure
mkdir -p ~/.hammerspoon/keys

# Symlink all Hammerspoon files
ln -s "$(pwd)/src/hammerspoon/ableton.lua" ~/.hammerspoon/
ln -s "$(pwd)/src/hammerspoon/app_watcher.lua" ~/.hammerspoon/
ln -s "$(pwd)/src/hammerspoon/config.lua" ~/.hammerspoon/
ln -s "$(pwd)/src/hammerspoon/live_state.lua" ~/.hammerspoon/
ln -s "$(pwd)/src/hammerspoon/status_check.lua" ~/.hammerspoon/
ln -s "$(pwd)/src/hammerspoon/utils.lua" ~/.hammerspoon/
ln -s "$(pwd)/src/hammerspoon/keys/navigation.lua" ~/.hammerspoon/keys/
ln -s "$(pwd)/src/hammerspoon/keys/editing.lua" ~/.hammerspoon/keys/
ln -s "$(pwd)/src/hammerspoon/keys/views.lua" ~/.hammerspoon/keys/
```

**Alternative (production):** Copy files:
```bash
cp -r src/hammerspoon/*.lua ~/.hammerspoon/
mkdir -p ~/.hammerspoon/keys
cp src/hammerspoon/keys/*.lua ~/.hammerspoon/keys/
```

### 7. Configure Hammerspoon

Add to your `~/.hammerspoon/init.lua`:

```lua
-- Load Ableton Live integration
require("ableton")
```

Then **reload Hammerspoon config** (Menu bar icon → Reload Config)

### 8. Verify Installation

**Check Remote Script is loaded:**
```bash
# View Ableton's log
tail -f ~/Library/Preferences/Ableton/Live\ */Log.txt
# Look for: "Live State Remote Script initialized"
```

**Test server connection:**
```bash
echo "GET_VIEW" | nc 127.0.0.1 9001
# Should return: {"view": "session"} or {"view": "arrangement"}
```

**Test in Hammerspoon console:**
```lua
liveState = require("live_state")
liveState.selectFirstTrack()
```

## Key Bindings

### Session View
- `gg` - Select first scene
- `G` - Select last scene
- `za` - Undo
- `dd` (double-tap) - Delete
- `ctrl + -` - Toggle browser

### Arrangement View
- `gg` - Select first track (scrolls view)
- `G` - Select last track (scrolls view)
- `za` - Undo
- `dd` (double-tap) - Delete
- `ctrl + -` - Toggle browser

## Available Commands

The Remote Script exposes these commands via socket (port 9001):

| Command | Description | Thread-Safe |
|---------|-------------|-------------|
| `GET_VIEW` | Returns current view (session/arrangement) | ✅ Fast path |
| `GET_STATE` | Returns full Live state (transport, views, etc.) | Via main thread |
| `SELECT_FIRST_SCENE` | Select first scene in Session view | Via main thread |
| `SELECT_LAST_SCENE` | Select last scene in Session view | Via main thread |
| `SELECT_FIRST_TRACK` | Select first track (auto-scrolls) | Via main thread |
| `SELECT_LAST_TRACK` | Select last track (auto-scrolls) | Via main thread |

### Adding New Commands

1. Add handler in `LiveState.py`:
```python
def _handle_your_command(self, params=None):
    """Handle YOUR_COMMAND"""
    # Your logic here using self.song()
    return {"success": True, "data": "..."}
```

2. Register in `_register_commands()`:
```python
"YOUR_COMMAND": self._handle_your_command,
```

3. Add wrapper in `live_state.lua`:
```lua
function M.yourCommand()
    return sendCommand("YOUR_COMMAND")
end
```

## Troubleshooting

### Remote Script not loading
- Check folder is named exactly `LiveState`
- View `~/Library/Preferences/Ableton/Live */Log.txt` for errors
- Ensure Python script has no syntax errors: `python3 -m py_compile src/remote_script/LiveState.py`

### Shortcuts stop working after a while
- **Fixed!** Eventtaps now auto-restart every 5 seconds if disabled
- Check Hammerspoon console for warnings: `"WARNING - eventtap was disabled, restarting..."`

### Server connection fails
```bash
# Check if server is running
lsof -i :9001

# Test manually
echo "GET_STATE" | nc 127.0.0.1 9001
```

### Commands are slow
- `GET_VIEW` uses fast path (no thread switching)
- Other commands use `schedule_message(0, ...)` for minimal latency
- Expected response time: 20-50ms

### Hammerspoon not detecting Live opening/closing
- **Fixed!** App watcher now stored at module level to prevent garbage collection
- Check console for: `"Ableton VimMode: Application watcher started"`

## WebSocket TreeViewer

VimAbl includes a real-time web-based AST visualizer for Ableton Live projects.

### Features
- 🌲 **Interactive Tree View** - Explore project structure (tracks, devices, clips, samples)
- ⚡ **Real-Time Updates** - See changes as you work in Live
- 🔍 **SHA Tracking** - Each file reference is hashed for diff detection
- 🧰 **WebSocket Streaming** - Efficient JSON-based communication

### Quick Start

**Automatic Mode (with Hammerspoon):**
1. Make sure your Ableton project is saved
2. Launch Ableton Live
3. Wait ~5 seconds - WebSocket server starts automatically
4. Open http://localhost:5173 in your browser

**Manual Mode:**
```bash
# Terminal 1: Start WebSocket server
uv run python -m src.main Example_Project/example.als --mode=websocket

# Terminal 2: Start Svelte dev server
cd src/web/frontend
npm run dev

# Open http://localhost:5173 in browser
```

### Manual Controls (with Hammerspoon)

| Keybinding | Action |
|------------|--------|
| `Cmd+Shift+W` | Toggle WebSocket server on/off |
| `Cmd+Shift+R` | Restart WebSocket server |
| `Cmd+Shift+I` | Show server status |

### Architecture

The TreeViewer consists of:
- **WebSocket Server** (Python, port 8765) - Parses .als files and streams AST updates
- **Svelte Frontend** (SvelteKit + Tailwind, port 5173) - Renders interactive tree visualization
- **Hammerspoon Integration** - Auto-starts server when Ableton launches

## Development

### Project Structure
```
src/
├── remote_script/          # Python Remote Script (runs inside Live)
│   ├── __init__.py
│   └── LiveState.py       # Main controller with socket server
└── hammerspoon/           # Lua automation scripts
    ├── ableton.lua        # Entry point
    ├── live_state.lua     # Server communication
    ├── app_watcher.lua    # Detect Live open/close
    ├── status_check.lua   # Connection verification
    ├── utils.lua          # Helper functions
    ├── config.lua         # Configuration
    └── keys/              # Keybinding modules
        ├── navigation.lua # gg, G commands
        ├── editing.lua    # dd, za commands
        └── views.lua      # View toggles
```

### Debug Logging

**Python (Ableton's Log.txt):**
```python
self.log_message("Your debug message")
```

**Hammerspoon (Console):**
```lua
print("Your debug message")
```

## Future Ideas

- Command palette overlay for fast navigation
- Lua plugin system for user extensions
- AI-powered auto-completion for different genres
- More Vim motions (hjkl navigation, visual mode, etc.)

## License

MIT

## Contributing

Contributions welcome! This is in active development with symlinks for rapid iteration.
