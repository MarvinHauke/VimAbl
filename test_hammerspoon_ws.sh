#!/bin/bash
# Test script to verify Hammerspoon WebSocket integration

echo "Testing Hammerspoon WebSocket Integration"
echo "=========================================="
echo ""

# Check if websocket_manager is symlinked
if [ -L ~/.hammerspoon/websocket_manager.lua ]; then
    echo "✓ websocket_manager.lua is symlinked"
else
    echo "✗ websocket_manager.lua is NOT symlinked"
    echo "  Run: ln -sf $(pwd)/src/hammerspoon/websocket_manager.lua ~/.hammerspoon/"
fi

# Check if Hammerspoon is running
if pgrep -q Hammerspoon; then
    echo "✓ Hammerspoon is running"
else
    echo "✗ Hammerspoon is NOT running"
    echo "  Start Hammerspoon first"
    exit 1
fi

echo ""
echo "To test the integration:"
echo "1. Reload Hammerspoon config: Press Cmd+Ctrl+R"
echo "2. Check Hammerspoon console for logs"
echo "3. Press Cmd+Shift+I to see WebSocket server status"
echo "4. Press Cmd+Shift+W to toggle WebSocket server"
echo ""
echo "Expected console output after reload:"
echo "  - 'Ableton VimMode: WebSocket keybindings loaded'"
echo "  - '  Cmd+Shift+W: Toggle WebSocket server'"
echo "  - '  Cmd+Shift+R: Restart WebSocket server'"
echo "  - '  Cmd+Shift+I: Show server status'"
echo ""

# Check if WebSocket server is already running
if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✓ WebSocket server is currently running on port 8765"
    PID=$(lsof -Pi :8765 -sTCP:LISTEN -t)
    echo "  PID: $PID"
    ps -p $PID -o command=
else
    echo "○ WebSocket server is not running"
    echo "  This is normal if you haven't started it yet"
fi

echo ""
