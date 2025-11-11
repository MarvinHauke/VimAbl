# VimAbl Setup Guide

## Overview

VimAbl has two separate Python environments:

1. **External Tools** (AST parser, WebSocket server, CLI)
   - Uses your system Python (3.11+)
   - Managed with `uv`
   - Dependencies: `websockets`, `aiohttp`, `watchdog`

2. **Ableton Remote Script** (`src/remote_script/`)
   - Runs inside Ableton Live's bundled Python
   - No external dependencies
   - Only uses: `Live`, `_Framework`, and standard library

## Installation

### 1. Install uv (if not already installed)

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
python -m src.main --help  # Works without uv run!
```

**Option 2: Use uv run**

```bash
uv run python -m src.main --help
```

**Option 3: Activate manually**

```bash
source .venv/bin/activate
python -m src.main --help
```

## Environment Variables

The `.envrc` file sets up useful environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VIMABL_WS_HOST` | `localhost` | WebSocket server host |
| `VIMABL_WS_PORT` | `8765` | WebSocket server port |
| `VIMABL_REMOTE_PORT` | `9001` | Remote Script socket port |
| `VIMABL_ENV` | `development` | Environment mode |
| `PROJECT_ROOT` | (auto) | Absolute path to project root |
| `ABLETON_USER_LIBRARY` | (auto) | Path to Ableton User Library |
| `ABLETON_REMOTE_SCRIPTS` | (auto) | Path to Remote Scripts folder |

### Local Overrides

Create `.envrc.local` (gitignored) for personal settings:

```bash
# .envrc.local example
export VIMABL_WS_PORT=9000
export VIMABL_ENV="production"
```

## Usage

### Running the AST Parser

```bash
# Show project info
uv run python -m src.main Example_Project/example.als --mode=info

# Output full AST
uv run python -m src.main Example_Project/example.als --mode=server

# Legacy mode (raw dict)
uv run python -m src.main Example_Project/example.als --mode=legacy
```

### Running the WebSocket Server

```bash
# Start WebSocket server on default port (8765)
uv run python -m src.main Example_Project/example.als --mode=websocket

# Custom host and port
uv run python -m src.main Example_Project/example.als --mode=websocket --ws-host=0.0.0.0 --ws-port=9000
```

### Testing WebSocket Connection

```bash
# Test with included test script
uv run python test_websocket.py
```

## Remote Script Setup (Separate)

The Remote Script (`src/remote_script/`) runs **inside** Ableton Live and requires no external dependencies.

### Installation

1. Create symlink to Remote Script:

```bash
# macOS
ln -s "$(pwd)/src/remote_script" ~/Music/Ableton/User\ Library/Remote\ Scripts/LiveState
```

2. Restart Ableton Live

3. Enable in Preferences → Link/Tempo/MIDI → Control Surface

4. Select "LiveState" from the dropdown

The Remote Script will start a socket server on port 9001 for communication with Hammerspoon.

## Dependency Management

### Adding New Dependencies

```bash
# Add a runtime dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Example: Add a new parser library
uv add lxml
```

### Updating Dependencies

```bash
# Update all packages
uv sync --upgrade

# Update specific package
uv add <package-name>@latest
```

### Removing Dependencies

```bash
uv remove <package-name>
```

## Development Workflow

### 1. Make Code Changes

Edit files in `src/` as needed.

### 2. Test Changes

```bash
# Run AST parser
uv run python -m src.main Example_Project/example.als --mode=info

# Start WebSocket server
uv run python -m src.main Example_Project/example.als --mode=websocket
```

### 3. Run Tests (when available)

```bash
uv run pytest
```

## Why Two Environments?

**External Tools (uv-managed):**
- Full access to PyPI packages
- Can use modern Python 3.11+
- Independent of Ableton

**Remote Script (Ableton's Python):**
- Must run inside Ableton's sandbox
- No pip/external packages allowed
- Only standard library + Live API
- Version depends on Ableton (typically Python 2.7 or 3.x)

This separation allows us to:
- Use modern Python features for external tools
- Keep Remote Script compatible with Ableton's constraints
- Maintain clean dependency isolation

## Troubleshooting

### "Module not found" Error

Make sure you're using `uv run`:

```bash
# ❌ Don't run directly
python -m src.main ...

# ✅ Use uv run
uv run python -m src.main ...

# Or activate venv first
source .venv/bin/activate
python -m src.main ...
```

### Remote Script Not Loading

The Remote Script has no external dependencies, so it should always work. If it's not loading:

1. Check symlink exists:
   ```bash
   ls -la ~/Music/Ableton/User\ Library/Remote\ Scripts/LiveState
   ```

2. Restart Ableton Live

3. Check Ableton's Log.txt for errors

### WebSocket Connection Refused

Make sure the server is running:

```bash
# Start server
uv run python -m src.main Example_Project/example.als --mode=websocket

# In another terminal, test connection
uv run python test_websocket.py
```

## Next Steps

- [Phase 2: Svelte Frontend Setup](TODO.md#phase-2-svelte-frontend-foundation)
- [Remote Script Integration](TODO.md#phase-5-remote-script-integration)
- [Contributing Guidelines](CONTRIBUTING.md) (if exists)
