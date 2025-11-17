# Extending VimAbl

Learn how to extend VimAbl with custom commands, keybindings, and modules.

!!! info "Coming Soon"
    This page will be fully documented in the next release. For now, see the source code examples below.

## Adding New Commands

### 1. Add Handler in Remote Script

Edit `src/remote_script/LiveState.py`:

```python
def _handle_your_command(self, params=None):
    """Handle YOUR_COMMAND"""
    try:
        # Your logic here using self.song()
        song = self.song()
        # ... your code ...
        return {"success": True, "data": "result"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 2. Register Command

In `_register_commands()`:

```python
def _register_commands(self):
    """Register all command handlers"""
    return {
        # ... existing commands ...
        "YOUR_COMMAND": self._handle_your_command,
    }
```

### 3. Add Lua Wrapper

Edit `src/hammerspoon/live_state.lua`:

```lua
function M.yourCommand()
    local response = sendCommand("YOUR_COMMAND")
    if response and response.success then
        return response.data
    end
    return nil
end
```

### 4. Add Keybinding

Create or edit a file in `src/hammerspoon/keys/`:

```lua
local liveState = require("live_state")

-- Define your keybinding
hs.hotkey.bind({"cmd"}, "y", function()
    if not isAbletonFrontmost() then return end
    liveState.yourCommand()
end)
```

## Adding New Observers

### 1. Create Observer Class

Edit `src/remote_script/observers.py`:

```python
class YourObserver:
    def __init__(self, parent, target, udp_sender):
        self.parent = parent
        self.target = target
        self.udp = udp_sender
        self.setup_listeners()

    def setup_listeners(self):
        # Add Live API listeners
        if self.target.some_property_has_listener:
            self.target.add_some_property_listener(self.on_some_property_changed)

    def on_some_property_changed(self):
        value = self.target.some_property
        self.udp.send("/live/your/event", [value])

    def cleanup(self):
        # Remove listeners
        if self.target.some_property_has_listener:
            self.target.remove_some_property_listener(self.on_some_property_changed)
```

### 2. Register Observer

In `LiveState.py`, add to `_setup_observers()`:

```python
def _setup_observers(self):
    # ... existing observers ...
    your_observer = YourObserver(self, self.song(), self.udp_sender)
    self.observers.append(your_observer)
```

## Adding New Keybinding Modules

### Create New Module

Create `src/hammerspoon/keys/your_module.lua`:

```lua
local liveState = require("live_state")
local utils = require("utils")

local M = {}

function M.init()
    -- Your keybindings here
    hs.hotkey.bind({"cmd"}, "k", function()
        if not utils.isAbletonFrontmost() then return end
        liveState.yourCommand()
    end)
end

return M
```

### Load Module

Edit `src/hammerspoon/ableton.lua`:

```lua
-- Require your module
local yourModule = require("keys/your_module")

-- Initialize it
yourModule.init()
```

## Customizing Existing Keybindings

### Edit Keybinding Files

Keybindings are in `src/hammerspoon/keys/`:

- `navigation.lua` - Navigation commands (gg, G)
- `editing.lua` - Editing commands (dd, za)
- `views.lua` - View toggles

### Example: Change Sequence Timeout

Edit `src/hammerspoon/config.lua`:

```lua
M.timeouts = {
    doubleTap = 500,    -- milliseconds (default)
    sequence = 750,     -- increase to 750ms for more time
}
```

## Project Structure for Extensions

```
src/
├── remote_script/
│   ├── LiveState.py        # Add commands here
│   ├── commands.py         # Or separate command files
│   └── observers.py        # Add observers here
│
└── hammerspoon/
    ├── live_state.lua      # Add command wrappers
    ├── config.lua          # Configuration
    └── keys/               # Add keybinding modules
        ├── navigation.lua
        ├── editing.lua
        ├── views.lua
        └── your_module.lua # Your new module
```

## Best Practices

### Thread Safety

Always use `schedule_message()` for Live API operations:

```python
def _handle_command(self, params=None):
    # Queue for main thread
    self.schedule_message(0, self._do_command, params)

def _do_command(self, params):
    # This runs on main thread - safe to use Live API
    song = self.song()
    # ... Live API calls ...
```

### Error Handling

Always wrap commands in try/except:

```python
def _handle_command(self, params=None):
    try:
        # Your code
        return {"success": True}
    except Exception as e:
        self.log_message(f"Error: {str(e)}")
        return {"success": False, "error": str(e)}
```

### Logging

Use consistent logging:

```python
# Python
self.log_message("Your message")

# Lua
print("Your message")  -- Visible in Hammerspoon console
```

## Testing Your Extensions

### Test Command via netcat

```bash
echo "YOUR_COMMAND" | nc 127.0.0.1 9001
```

### Test Keybinding

1. Reload Hammerspoon config
2. Open Hammerspoon console
3. Press your keybinding
4. Check console for errors

### Test Observer

```bash
# Start UDP listener
python3 src/udp_listener/listener.py

# Make changes in Ableton
# Watch for events in listener output
```

## Examples

See existing implementations:
- [LiveState.py](https://github.com/yourusername/VimAbl/blob/main/src/remote_script/LiveState.py)
- [navigation.lua](https://github.com/yourusername/VimAbl/blob/main/src/hammerspoon/keys/navigation.lua)
- [observers.py](https://github.com/yourusername/VimAbl/blob/main/src/remote_script/observers.py)

## Contributing

Want to contribute your extension?

1. Fork the repository
2. Create a feature branch
3. Add your extension
4. Test thoroughly
5. Submit a pull request

See [CONTRIBUTING.md](https://github.com/yourusername/VimAbl/blob/main/CONTRIBUTING.md)
