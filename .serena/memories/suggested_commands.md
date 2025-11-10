# Suggested Commands

## Development Setup

### Install Remote Script (Symlink for Development)
```bash
ln -s "$(pwd)/src/remote_script" ~/Music/Ableton/User\ Library/Remote\ Scripts/LiveState
```

### Install Hammerspoon Scripts (Symlink for Development)
```bash
mkdir -p ~/.hammerspoon/keys
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

## Testing & Verification

### Check Remote Script Loaded
```bash
tail -f ~/Library/Preferences/Ableton/Live\ */Log.txt
# Look for: "Live State Remote Script initialized"
```

### Test Socket Server Connection
```bash
echo "GET_VIEW" | nc 127.0.0.1 9001
# Should return: {"view": "session"} or {"view": "arrangement"}
```

### Test Full State Query
```bash
echo "GET_STATE" | nc 127.0.0.1 9001
```

### Check Server Port is Running
```bash
lsof -i :9001
```

### Test in Hammerspoon Console
```lua
liveState = require("live_state")
liveState.selectFirstTrack()
```

## Code Validation

### Python Syntax Check
```bash
python3 -m py_compile src/remote_script/LiveState.py
```

### Check Lua Syntax (if luac available)
```bash
luac -p src/hammerspoon/*.lua
```

## Git Commands
```bash
# Standard git workflow
git status
git add .
git commit -m "message"
git push

# View recent commits
git log --oneline -5
```

## Debugging

### Monitor Ableton Log (Python)
```bash
tail -f ~/Library/Preferences/Ableton/Live\ */Log.txt
```

### View Hammerspoon Console
Open Hammerspoon → Console (from menu bar)

### Reload Hammerspoon Config
Hammerspoon menu bar icon → Reload Config

## macOS Specific Commands

### List Directory
```bash
ls -la
```

### Find Files
```bash
find . -name "*.py"
find . -name "*.lua"
```

### Search in Files (ripgrep/grep)
```bash
rg "pattern" src/
grep -r "pattern" src/
```

## Running the Project

1. **Start Ableton Live** - Remote Script auto-loads
2. **Hammerspoon runs automatically** - App watcher detects Live
3. **Use keybindings** - `gg`, `G`, `dd`, `za`, etc.

## Notes
- No formal testing framework currently in place
- No linting/formatting tools configured (pylint, black, flake8, etc.)
- Development uses symlinks for rapid iteration
- Manual testing via socket commands and Live interaction
