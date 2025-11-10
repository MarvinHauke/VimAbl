# Coding Style and Conventions

## Python (Remote Script)

### General Style
- **Naming**: snake_case for variables, methods, and functions
- **Classes**: PascalCase (e.g., `LiveState`)
- **Private methods**: Prefix with underscore (e.g., `_setup_observers`, `_on_view_changed`)
- **Docstrings**: Triple-quoted strings at module and method level
  ```python
  """
  Main Remote Script controller that observes Live's state
  """
  ```

### Code Patterns
- **Inheritance**: Extends `ControlSurface` from Live's `_Framework`
- **Thread safety**: Uses `threading.Lock()` and `threading.Event()` for synchronization
- **Error handling**: Try-except blocks for observer registration (RuntimeError for duplicates)
- **Logging**: Use `self.log_message()` for debug output to Ableton's Log.txt

### Type Hints
- Not extensively used in current codebase
- Focus on clear variable names and comments instead

### Example Pattern
```python
def _handle_command(self, params=None):
    """Handle COMMAND_NAME"""
    # Implementation using self.song()
    return {"success": True, "data": "..."}
```

## Lua (Hammerspoon Scripts)

### General Style
- **Naming**: camelCase for functions and variables (e.g., `getCurrentView`, `selectFirstTrack`)
- **Module pattern**: Use `local M = {}` and `return M`
- **Constants**: UPPER_CASE in module tables (e.g., `M.HOST`, `M.PORT`)

### Code Patterns
- **Modules**: All files return a module table (`local M = {}; return M`)
- **Setup functions**: Each module has `M.setup()` for initialization
- **Cleanup functions**: Provide `M.stop()` for teardown
- **Print debugging**: Use `print()` for console output
- **Eventtap monitoring**: Auto-restart disabled eventtaps every 5 seconds

### Configuration
- Timeouts and configuration in separate `config.lua` module
- Tab indentation (not spaces)

### Example Pattern
```lua
local M = {}

function M.commandName()
    return sendCommand("COMMAND_NAME")
end

function M.setup()
    -- Initialize
end

return M
```

## Comments
- **Python**: Use inline comments for complex logic, docstrings for functions/classes
- **Lua**: Use `--` for single-line comments, descriptive function documentation

## File Organization
- Keep related functionality in separate modules
- Python: One main class per file
- Lua: One module per file, organized in subdirectories (e.g., `keys/`)
