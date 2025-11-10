# Codebase Structure

## Directory Layout

```
Ableton-Live-LSP/
├── .claude/                    # Claude configuration
├── .git/                       # Git repository
├── .serena/                    # Serena memory files
├── Example_Project/            # Test project files
│   ├── example.als            # Ableton project file
│   └── example.xml            # Decompressed XML for testing
├── src/                        # Source code
│   ├── main.py                # CLI entrypoint (legacy/server/info modes)
│   ├── parser/                # XML parsing and data extraction
│   │   ├── __init__.py
│   │   ├── xml_loader.py      # Decompress .als, load XML tree
│   │   ├── file_refs.py       # Extract FileRef + hashes
│   │   ├── tracks.py          # Extract track information
│   │   ├── ast_builder.py     # Build raw dict AST
│   │   └── utils.py           # Shared helpers
│   ├── ast/                   # AST node classes and manipulation
│   │   ├── __init__.py
│   │   ├── node.py            # Node class definitions
│   │   ├── visitor.py         # Traversals, diffing, serialization
│   │   └── hashing.py         # Incremental SHA-256 per node
│   ├── server/                # LSP-like server interface
│   │   ├── __init__.py
│   │   ├── api.py             # ASTServer with query/diff APIs
│   │   └── watcher.py         # File monitoring (optional)
│   ├── hammerspoon/           # Lua automation scripts
│   │   ├── ableton.lua        # Entry point for Hammerspoon integration
│   │   ├── app_watcher.lua    # Detects Live open/close events
│   │   ├── config.lua         # Configuration (timeouts, settings)
│   │   ├── live_state.lua     # Socket client, command wrappers
│   │   ├── status_check.lua   # Connection verification
│   │   ├── utils.lua          # Helper functions (sequence detection, etc.)
│   │   ├── test_commands.lua  # Testing utilities
│   │   └── keys/              # Keybinding modules
│   │       ├── navigation.lua # gg, G navigation commands
│   │       ├── editing.lua    # dd, za editing commands
│   │       └── views.lua      # View toggles (ctrl + -)
│   └── remote_script/         # Python Remote Script (runs inside Live)
│       ├── __init__.py        # Required for Python package
│       ├── LiveState.py       # Main controller with socket server
│       ├── commands.py        # Command implementations
│       ├── observers.py       # Live API observers
│       └── server.py          # Socket server
├── requirements.txt           # Python dependencies (watchdog)
├── .gitignore                 # Git ignore patterns
├── .mcp.json                  # MCP configuration
├── LICENSE                    # MIT License
├── Log.txt                    # Project log file
├── REFACTORING_SUMMARY.md     # AST refactoring documentation
└── README.md                  # Project documentation
```

## Key Files and Their Roles

### AST Parser & Server (new - 2025-11-10)

#### `src/main.py`
- **CLI entrypoint** with three modes:
  - `--mode=legacy` - Raw dict output (backward compatible)
  - `--mode=server` - Structured AST with node objects
  - `--mode=info` - Project statistics summary

#### `src/parser/` - XML Parsing Module
- `xml_loader.py` - Decompress .als files, load XML tree
- `file_refs.py` - Extract file references and hashes
- `tracks.py` - Extract track information
- `ast_builder.py` - Build raw dict AST from XML
- `utils.py` - Shared helper functions

#### `src/ast/` - AST Manipulation Module
- `node.py` - Node class definitions (ProjectNode, TrackNode, DeviceNode, etc.)
- `visitor.py` - Visitor patterns (serialization, diffing, search, pretty-print)
- `hashing.py` - Incremental SHA-256 hashing for change detection

#### `src/server/` - LSP-like Server Interface
- `api.py` - ASTServer with query, diff, and project info APIs
- `watcher.py` - File monitoring with automatic reloading (optional, requires watchdog)

### Python Remote Script (runs inside Ableton Live)

#### `src/remote_script/LiveState.py`
- **Main controller class** extending `ControlSurface`
- Manages socket server on port 9001
- Handles thread-safe command execution
- Observes Live's view changes (Session/Arrangement)
- Implements command handlers for Hammerspoon

Key responsibilities:
- Socket server thread management
- Command routing and execution
- Observer setup for view changes
- Thread synchronization with locks and events

### Lua Hammerspoon Scripts (runs on macOS)

#### `src/hammerspoon/ableton.lua`
- **Entry point** for Hammerspoon integration
- Loaded from `~/.hammerspoon/init.lua`
- Coordinates other modules

#### `src/hammerspoon/live_state.lua`
- **Socket client** for communicating with Remote Script
- Command wrapper functions (selectFirstTrack, getCurrentView, etc.)
- Handles TCP communication to port 9001

#### `src/hammerspoon/app_watcher.lua`
- Monitors Ableton Live application state
- Starts/stops keybindings when Live opens/closes
- Prevents garbage collection of watcher

#### `src/hammerspoon/config.lua`
- Configuration constants
- Timeout settings (doubleTap, sequence)

#### `src/hammerspoon/utils.lua`
- Helper functions for keybinding sequences
- Double-tap detection
- Eventtap creation utilities

#### `src/hammerspoon/status_check.lua`
- Connection verification
- Health monitoring

#### Keybinding Modules (`src/hammerspoon/keys/`)

**`navigation.lua`**
- `gg` - Jump to first scene/track
- `G` - Jump to last scene/track
- Auto-restart eventtaps every 5 seconds

**`editing.lua`**
- `dd` - Delete (double-tap)
- `za` - Undo

**`views.lua`**
- `ctrl + -` - Toggle browser
- Other view toggles

## Data Flow

1. **User presses key** → Hammerspoon eventtap catches it
2. **Eventtap handler** → Checks if Ableton is frontmost app
3. **Command wrapper** → Calls function in `live_state.lua`
4. **Socket client** → Sends command to port 9001
5. **Remote Script** → Receives command in socket thread
6. **Thread synchronization** → Queues command for main thread
7. **Command handler** → Executes using Live API
8. **Response** → Returns JSON result to Hammerspoon
9. **User sees result** → Action executed in Live

## Extension Points

### Working with AST Parser

1. **Add new node types**: Extend `src/ast/node.py` with new node classes
2. **Add new visitors**: Implement `ASTVisitor` subclass in `src/ast/visitor.py`
3. **Expand parser**: Add extraction functions in `src/parser/` modules
4. **Add server operations**: Extend `ASTServer` in `src/server/api.py`

### Adding New Commands

1. **Python**: Add handler in `LiveState.py` and register in `_register_commands()`
2. **Lua**: Add wrapper function in `live_state.lua`
3. **Keybinding**: Create new module in `keys/` or add to existing module

### Adding New Views/Observers

1. **Python**: Add observer in `_setup_observers()` method
2. **Python**: Add callback method (e.g., `_on_view_changed`)
3. **Update state**: Store state in instance variables

## Dependencies

### Python
- `Live` - Ableton Live API (bundled with Live)
- `_Framework.ControlSurface` - Base class for Remote Scripts
- Standard library: `socket`, `threading`, `json`

### Lua
- Hammerspoon framework (installed separately)
- Standard Lua 5.4 library
