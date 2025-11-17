# Troubleshooting

Common issues and solutions for VimAbl.

## Installation Issues

### Remote Script Not Loading

**Symptom:** Ableton Live doesn't show LiveState in Control Surface dropdown

**Solutions:**

1. ✅ **Check folder name** - Must be exactly `LiveState`
   ```bash
   ls ~/Music/Ableton/User\ Library/Remote\ Scripts/
   # Should show: LiveState
   ```

2. ✅ **Check Python syntax**
   ```bash
   python3 -m py_compile src/remote_script/LiveState.py
   # Should complete without errors
   ```

3. ✅ **View Ableton's log**
   ```bash
   tail -f ~/Library/Preferences/Ableton/Live\ */Log.txt
   # Look for: "Live State Remote Script initialized"
   ```

4. ✅ **Restart Ableton Live completely**

### Hammerspoon Not Detecting Live

**Symptom:** Keybindings don't work when Ableton is frontmost

**Solutions:**

1. ✅ **Check Hammerspoon console**
   - Look for: `"Ableton VimMode: Application watcher started"`
   - Check for errors

2. ✅ **Verify accessibility permissions**
   - System Preferences → Security & Privacy → Privacy → Accessibility
   - Ensure Hammerspoon is checked

3. ✅ **Reload Hammerspoon config**
   - Menu bar icon → Reload Config

## Connection Issues

### Server Connection Fails

**Symptom:** `nc 127.0.0.1 9001` doesn't connect

**Solutions:**

1. ✅ **Check if server is running**
   ```bash
   lsof -i :9001
   # Should show Python process
   ```

2. ✅ **Restart Ableton Live**

3. ✅ **Check firewall settings**
   - Ensure localhost connections are allowed

### UDP Events Not Received

**Symptom:** UDP listener shows no events

**Solutions:**

1. ✅ **Check listener is running**
   ```bash
   lsof -i :9002
   # Should show Python process
   ```

2. ✅ **Verify observers are active**
   ```bash
   echo "GET_OBSERVER_STATUS" | nc localhost 9001
   # Should return observer statistics
   ```

3. ✅ **Restart observers**
   ```bash
   echo "STOP_OBSERVERS" | nc localhost 9001
   echo "START_OBSERVERS" | nc localhost 9001
   ```

## Keybinding Issues

### Commands Not Working

**Symptom:** Pressing `gg` or other commands does nothing

**Solutions:**

1. ✅ **Ensure Ableton is frontmost app**
   - Commands only work when Live has focus

2. ✅ **Check sequence timing**
   - Press keys within 500ms
   - Try pressing slightly faster

3. ✅ **Verify eventtap is running**
   - Check Hammerspoon console
   - Eventtaps auto-restart every 5 seconds

4. ✅ **Reload Hammerspoon config**

### Wrong Command Executes

**Symptom:** `gg` does the wrong action

**Solutions:**

1. ✅ **Check current view**
   ```bash
   echo "GET_VIEW" | nc 127.0.0.1 9001
   # Returns: {"view": "session"} or {"view": "arrangement"}
   ```

2. ✅ **Verify view matches what you see in Ableton**

3. ✅ **Restart Ableton Live**

## WebSocket Issues

### TreeViewer Not Loading

**Symptom:** `http://localhost:5173` doesn't load

**Solutions:**

1. ✅ **Check Svelte dev server is running**
   ```bash
   cd src/web/frontend
   npm run dev
   # Should start on port 5173
   ```

2. ✅ **Check port availability**
   ```bash
   lsof -i :5173
   ```

3. ✅ **Try manual mode**
   ```bash
   uv run python -m src.main Example_Project/example.als --mode=websocket
   ```

### WebSocket Server Not Starting

**Symptom:** Server won't start automatically

**Solutions:**

1. ✅ **Ensure project is saved**
   - Server needs a valid `.als` file

2. ✅ **Check port 8765**
   ```bash
   lsof -i :8765
   # Kill if in use: lsof -ti :8765 | xargs kill
   ```

3. ✅ **Check Hammerspoon console for errors**

## Performance Issues

### Commands Are Slow

**Symptom:** Commands take > 1 second to execute

**Solutions:**

1. ✅ **Check server latency**
   ```bash
   time echo "GET_VIEW" | nc 127.0.0.1 9001
   # Should be < 50ms
   ```

2. ✅ **Restart Ableton Live**
   - Sometimes Live's API slows down after extended use

3. ✅ **Check CPU usage**
   - Remote Script should use < 5% CPU

### High CPU Usage

**Symptom:** Remote Script uses excessive CPU

**Solutions:**

1. ✅ **Check observer status**
   ```bash
   echo "GET_OBSERVER_STATUS" | nc localhost 9001
   ```

2. ✅ **Stop observers temporarily**
   ```bash
   echo "STOP_OBSERVERS" | nc localhost 9001
   ```

3. ✅ **Check for excessive events**
   - Look for stuck observers or infinite loops

## Debug Mode

### Enable Verbose Logging

**Remote Script:**
Add to `LiveState.py`:
```python
self.log_message("DEBUG: Your message here")
```

View in log:
```bash
tail -f ~/Library/Preferences/Ableton/Live\ */Log.txt
```

**Hammerspoon:**
Add to any `.lua` file:
```lua
print("DEBUG: Your message here")
```

View in Hammerspoon console.

## Getting Help

If none of these solutions work:

1. **Check the FAQ** - [FAQ](faq.md)
2. **Search GitHub Issues** - Previous solutions
3. **Open a New Issue** - Include:
   - Error messages
   - Log excerpts
   - Steps to reproduce
   - System information (macOS version, Live version)

## System Information

Useful for bug reports:

```bash
# macOS version
sw_vers

# Ableton Live version
# (visible in Ableton → About Ableton Live)

# Python version
python3 --version

# Hammerspoon version
# (visible in Hammerspoon → About)

# Check ports
lsof -i :9001 -i :9002 -i :8765
```
