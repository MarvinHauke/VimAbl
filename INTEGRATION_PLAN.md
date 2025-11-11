# WebSocket Server Integration Plan

## Recommended Approach: Hammerspoon Integration

### Why Hammerspoon?

1. ✅ **Already running** - You use Hammerspoon for vim keybindings
2. ✅ **Can manage processes** - Start/stop WebSocket server
3. ✅ **Detects Ableton state** - Already watches Ableton launch/quit
4. ✅ **System Python access** - Not limited by Ableton's Python
5. ✅ **Easy to debug** - Logs visible in Hammerspoon console

### Implementation Steps

#### 1. Create WebSocket Manager Module

```lua
-- src/hammerspoon/websocket_manager.lua

local M = {}

M.wsTask = nil
M.port = 8765
M.projectPath = nil

-- Start WebSocket server for a project
function M.start(projectPath)
    M.stop()  -- Stop any existing server

    if not projectPath then
        print("[WebSocket] No project path provided")
        return
    end

    M.projectPath = projectPath

    local uvPath = hs.execute("which uv"):gsub("%s+", "")
    local projectRoot = os.getenv("HOME") .. "/Development/python/VimAbl"

    print("[WebSocket] Starting server for: " .. projectPath)

    M.wsTask = hs.task.new(
        uvPath,
        function(exitCode, stdOut, stdErr)
            if exitCode == 0 then
                print("[WebSocket] Server stopped cleanly")
            else
                print("[WebSocket] Server error: " .. stdErr)
            end
        end,
        function(task, stdOut, stdErr)
            -- Stream output to console
            if stdOut then print("[WebSocket] " .. stdOut) end
            if stdErr then print("[WebSocket ERROR] " .. stdErr) end
            return true
        end,
        {
            "run",
            "python",
            "-m",
            "src.main",
            projectPath,
            "--mode=websocket",
            "--ws-port=" .. M.port
        }
    )

    M.wsTask:setWorkingDirectory(projectRoot)
    M.wsTask:start()

    print("[WebSocket] Server started on port " .. M.port)
end

-- Stop WebSocket server
function M.stop()
    if M.wsTask then
        M.wsTask:terminate()
        M.wsTask = nil
    end

    -- Also kill any orphaned processes
    hs.execute("lsof -ti :" .. M.port .. " | xargs kill -9 2>/dev/null")

    print("[WebSocket] Server stopped")
end

-- Check if server is running
function M.isRunning()
    local output = hs.execute("lsof -ti :" .. M.port)
    return output and output:len() > 0
end

-- Restart server with current project
function M.restart()
    if M.projectPath then
        M.start(M.projectPath)
    end
end

return M
```

#### 2. Update App Watcher

```lua
-- src/hammerspoon/app_watcher.lua

local liveState = require("live_state")
local wsManager = require("websocket_manager")

local function onAbletonLaunched()
    print("Ableton Live launched")

    -- Wait a bit for Live to fully load
    hs.timer.doAfter(2, function()
        -- Get current project path from Remote Script
        local status, result = liveState.getStatus()
        if status and result.project_path then
            wsManager.start(result.project_path)
        end
    end)
end

local function onAbletonActivated()
    print("Ableton Live activated")
    -- Enable keybindings
end

local function onAbletonDeactivated()
    print("Ableton Live deactivated")
    -- Disable keybindings but keep WebSocket running
end

local function onAbletonQuit()
    print("Ableton Live quit")
    wsManager.stop()
end

-- Create watcher
local appWatcher = hs.application.watcher.new(function(appName, eventType, app)
    if appName == "Ableton Live" then
        if eventType == hs.application.watcher.launched then
            onAbletonLaunched()
        elseif eventType == hs.application.watcher.activated then
            onAbletonActivated()
        elseif eventType == hs.application.watcher.deactivated then
            onAbletonDeactivated()
        elseif eventType == hs.application.watcher.terminated then
            onAbletonQuit()
        end
    end
end)

appWatcher:start()

return {
    watcher = appWatcher,
    onAbletonLaunched = onAbletonLaunched,
    onAbletonQuit = onAbletonQuit
}
```

#### 3. Add Remote Script Command for Project Path

```python
# src/remote_script/commands.py

def _handle_get_project_path(self):
    """Get the current project path."""
    document = self.application.get_document()
    if document and hasattr(document, 'path'):
        path = document.path
        return {"project_path": str(path) if path else None}
    return {"project_path": None}

# Register in LiveState.py
self._register_command("GET_PROJECT_PATH", self._handle_get_project_path)
```

#### 4. Add Hammerspoon Keybinding for Manual Control

```lua
-- src/hammerspoon/keys/websocket.lua

local wsManager = require("websocket_manager")

-- Cmd+Shift+W - Toggle WebSocket server
hs.hotkey.bind({"cmd", "shift"}, "W", function()
    if wsManager.isRunning() then
        wsManager.stop()
        hs.alert.show("WebSocket Server Stopped")
    else
        -- Get current project from Live
        local status, result = liveState.sendCommand("GET_PROJECT_PATH")
        if status and result.project_path then
            wsManager.start(result.project_path)
            hs.alert.show("WebSocket Server Started")
        else
            hs.alert.show("No project loaded in Live")
        end
    end
end)

-- Cmd+Shift+R - Restart WebSocket server
hs.hotkey.bind({"cmd", "shift"}, "R", function()
    wsManager.restart()
    hs.alert.show("WebSocket Server Restarted")
end)
```

### Usage

Once implemented, the flow is:

1. **Open Ableton Live** → Hammerspoon detects launch
2. **Hammerspoon waits 2s** → Lets Live fully load
3. **Queries Remote Script** → Gets current project path
4. **Starts WebSocket server** → Automatically serves AST
5. **Open browser to localhost:5173** → See live visualization
6. **Close Ableton** → WebSocket server stops automatically

### Manual Controls

- `Cmd+Shift+W` - Toggle WebSocket server on/off
- `Cmd+Shift+R` - Restart WebSocket server
- Check status: Hammerspoon console logs

### Advantages

- ✅ **Automatic** - No manual steps needed
- ✅ **Reliable** - Hammerspoon handles process management
- ✅ **Debuggable** - All logs in Hammerspoon console
- ✅ **Flexible** - Manual controls available
- ✅ **Clean** - Remote Script stays simple
- ✅ **Integrates** - Works with existing keybindings

---

## Alternative: Simple Shell Script (Quick Start)

For now, you can also just use a simple script:

```bash
#!/bin/bash
# scripts/start_treeviewer.sh

# Get the currently open project (you'd need to implement this)
PROJECT_PATH="$1"

if [ -z "$PROJECT_PATH" ]; then
    echo "Usage: $0 <path-to-project.als>"
    exit 1
fi

# Start WebSocket server
echo "Starting WebSocket server..."
uv run python -m src.main "$PROJECT_PATH" --mode=websocket &
WS_PID=$!

# Start Svelte dev server
echo "Starting Svelte dev server..."
cd src/web/frontend
npm run dev &
SVELTE_PID=$!

# Trap exit and kill both processes
trap "kill $WS_PID $SVELTE_PID 2>/dev/null" EXIT INT TERM

echo ""
echo "🎉 TreeViewer running!"
echo "   WebSocket: ws://localhost:8765"
echo "   Browser:   http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait
wait
```

Usage:
```bash
./scripts/start_treeviewer.sh Example_Project/example.als
```

---

## Next Steps

1. **Phase 2 Complete** ✅ - Frontend working
2. **Choose integration** - Implement Hammerspoon integration
3. **Phase 3** - Add tree component with expand/collapse
4. **Phase 4** - Add real-time diff visualization
5. **Phase 5** - Integrate with Remote Script for live updates

Would you like me to implement the Hammerspoon integration now?
