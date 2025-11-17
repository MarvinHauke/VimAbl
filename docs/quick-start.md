# Quick Start Guide

Get up and running with VimAbl in 5 minutes!

!!! success "Prerequisites"
    Make sure you've completed the [Installation Guide](installation.md) first.

## Step 1: Launch Ableton Live

1. Open Ableton Live
2. Load any project (or start a new one)
3. Verify the Remote Script is loaded:
   ```bash
   echo "GET_VIEW" | nc 127.0.0.1 9001
   ```
   You should see: `{"view": "session"}` or `{"view": "arrangement"}`

## Step 2: Try Your First Commands

### In Session View

Make sure you're in Session View (Tab to switch views if needed).

**Jump to First Scene:**
```
Press: g g (quickly, twice)
```
Your view should jump to the first scene.

**Jump to Last Scene:**
```
Press: Shift + G
```
Your view should jump to the last scene.

### In Arrangement View

Switch to Arrangement View (Tab).

**Jump to First Track:**
```
Press: g g (quickly, twice)
```
The first track should be selected and the view should scroll to it.

**Jump to Last Track:**
```
Press: Shift + G
```
The last track should be selected and the view should scroll to it.

## Step 3: Try Editing Commands

**Undo:**
```
Press: z a
```
This triggers Ableton's undo function.

**Delete (Double-tap):**
```
Press: d d (quickly, twice)
```
This triggers delete on the selected item.

**Toggle Browser:**
```
Press: Ctrl + -
```
The device browser should toggle open/closed.

## Step 4: Explore the Web TreeViewer

The TreeViewer provides real-time visualization of your Ableton project.

### Automatic Mode (Recommended)

1. Make sure your Ableton project is **saved**
2. Launch Ableton Live
3. Wait ~5 seconds (WebSocket server starts automatically)
4. Open [http://localhost:5173](http://localhost:5173) in your browser

You should see a tree visualization of your project!

### Manual Mode

```bash
# Terminal 1: Start WebSocket server
uv run python -m src.main Example_Project/example.als --mode=websocket

# Terminal 2: Start Svelte dev server
cd src/web/frontend
npm run dev

# Open http://localhost:5173 in browser
```

### Try It Out

1. In the web UI, expand tracks and devices
2. In Ableton Live, rename a track
3. Watch the UI update in real-time!
4. Try changing track colors, adding devices, etc.

## Step 5: Check Real-Time Observers

VimAbl includes UDP/OSC observers that stream Live events in real-time.

### Start the UDP Listener

```bash
# Terminal 1: Start listener
python3 src/udp_listener/listener.py
```

### Make Changes in Ableton

- Rename a track → See event in terminal
- Mute/unmute a track → See event in terminal
- Adjust volume → See debounced events
- Change tempo → See event in terminal

### Check Observer Status

```bash
echo "GET_OBSERVER_STATUS" | nc localhost 9001
```

You should see statistics about active observers.

## Common Keybindings

### Session View

| Keybinding | Action |
|------------|--------|
| `gg` | Jump to first scene |
| `G` | Jump to last scene |
| `za` | Undo |
| `dd` | Delete (double-tap) |
| `Ctrl + -` | Toggle browser |

### Arrangement View

| Keybinding | Action |
|------------|--------|
| `gg` | Jump to first track (with scroll) |
| `G` | Jump to last track (with scroll) |
| `za` | Undo |
| `dd` | Delete (double-tap) |
| `Ctrl + -` | Toggle browser |

### Web TreeViewer Controls

| Keybinding | Action |
|------------|--------|
| `Cmd+Shift+W` | Toggle WebSocket server |
| `Cmd+Shift+R` | Restart WebSocket server |
| `Cmd+Shift+I` | Show server status |

## Next Steps

Now that you've got the basics, dive deeper:

- **[User Guide](user-guide/overview.md)** - Learn all features in detail
- **[Keybindings Reference](user-guide/keybindings.md)** - Complete command list
- **[Architecture](architecture/overview.md)** - Understand how it works
- **[Development Guide](development/extending.md)** - Extend VimAbl with your own commands

## Troubleshooting

### Commands Not Working

1. ✅ Check Ableton Live is the frontmost application
2. ✅ Verify Hammerspoon is running (menu bar icon)
3. ✅ Check Hammerspoon console for errors
4. ✅ Reload Hammerspoon config

### WebSocket Server Not Starting

1. ✅ Make sure your project is saved (`.als` file exists)
2. ✅ Check port 8765 is not in use: `lsof -i :8765`
3. ✅ Check Hammerspoon console for errors
4. ✅ Try manual mode to debug

### UDP Events Not Appearing

1. ✅ Check listener is running: `lsof -i :9002`
2. ✅ Verify Remote Script is loaded (check Log.txt)
3. ✅ Restart Ableton Live
4. ✅ Check observer status: `echo "GET_OBSERVER_STATUS" | nc localhost 9001`

Need more help? Check the [Full Troubleshooting Guide](troubleshooting.md).
