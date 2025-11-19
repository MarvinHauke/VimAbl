# GEMINI.md - VimAbl Project

This document provides a comprehensive overview of the VimAbl project, its architecture, and development conventions to be used as a context for future interactions.

## Project Overview

VimAbl is a sophisticated project that integrates Vim-like keyboard control into Ableton Live, coupled with a real-time project visualization tool. It enables users to navigate and control their Ableton Live sessions using keyboard shortcuts, while a web-based interface displays the project's structure in real-time.

The project is comprised of several key components:

*   **Python Remote Script (`src/remote_script`):** This script runs inside Ableton Live as a Control Surface. It's responsible for:
    *   Observing the state of the Ableton Live project (tracks, devices, scenes, etc.).
    *   Sending real-time updates via UDP/OSC to a listener.
    *   Running a TCP server to receive commands (e.g., from Hammerspoon).

*   **Hammerspoon (Lua) Scripts (`src/hammerspoon`):** These scripts run on macOS and are used to:
    *   Capture keyboard input to trigger commands.
    *   Send commands to the Python Remote Script's TCP server.
    *   Manage the lifecycle of the WebSocket server.

*   **WebSocket Server (`src/main.py`, `src/server`):** This is a Python application that:
    *   Parses the Ableton Live project file (`.als`) into an Abstract Syntax Tree (AST).
    *   Runs a WebSocket server to broadcast the AST to connected clients (the web UI).
    *   Includes a UDP listener (`src/udp_listener`) to receive real-time updates from the Python Remote Script and apply them to the AST.
    *   Watches the project file for changes and sends out diffs to the web UI.

*   **Svelte Frontend (`src/web/frontend`):** A web-based interface that:
    *   Connects to the WebSocket server.
    *   Renders a real-time, interactive tree view of the Ableton Live project.
    *   Highlights the currently selected track or clip.

## Building and Running

The project uses `uv` for Python package management.

### Installation

1.  **Install `uv`:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Clone the repository and sync dependencies:**
    ```bash
    git clone https://github.com/MarvinHauke/VimAbl.git
    cd VimAbl
    uv sync
    ```

### Running the WebSocket Server

The WebSocket server can be run manually for development or testing purposes.

```bash
# Start the WebSocket server
uv run python -m src.main path/to/project.als --mode=websocket
```

### Running Tests

The project uses `pytest` for testing.

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

### Building Documentation

The documentation is built using `mkdocs`.

```bash
# Install docs dependencies
uv pip install mkdocs mkdocs-material mkdocs-git-revision-date-localized-plugin

# Serve docs locally
mkdocs serve
```

## Development Conventions

### Project Structure

The project is organized as follows:

```
VimAbl/
├── src/
│   ├── remote_script/    # Python Remote Script (runs inside Live)
│   ├── hammerspoon/      # Lua automation scripts for Hammerspoon
│   ├── server/           # WebSocket and AST server
│   ├── udp_listener/     # UDP/OSC event receiver
│   └── web/frontend/     # Svelte web UI
├── docs/                 # MkDocs documentation
├── tests/                # Pytest tests
└── tools/                # Utility and test scripts
```

### Adding New Commands

New commands can be added by following these steps:

1.  **Add a handler** in the `CommandHandlers` class in `src/remote_script/commands.py`.
2.  **Register the command** in the `CommandServer` in `src/remote_script/server.py`.
3.  **Add a corresponding function** in the Hammerspoon scripts (`src/hammerspoon/live_state.lua`) to send the new command.

### Contribution Guidelines

*   Fork the repository and create a feature branch.
*   Make changes and test them thoroughly.
*   Commit the changes and open a pull request.
*   The development setup uses symlinks for rapid iteration.
