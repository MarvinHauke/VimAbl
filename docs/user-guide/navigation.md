# Navigation

Learn how to navigate efficiently in Ableton Live using Vim-style keybindings.

## Core Navigation Commands

### Jump to Beginning: `gg`

The `gg` command (press `g` twice quickly) jumps to the beginning of your current view:

**In Session View:**
- Selects the **first scene**
- Scrolls the view to show scene 1

**In Arrangement View:**
- Selects the **first track**
- Scrolls the track list to the top

**Usage:**
```
Press: g g (within 500ms)
```

### Jump to End: `G`

The `G` command (Shift + g) jumps to the end of your current view:

**In Session View:**
- Selects the **last scene**
- Scrolls the view to show the final scene

**In Arrangement View:**
- Selects the **last track**
- Scrolls the track list to the bottom

**Usage:**
```
Press: Shift + G
```

## How Navigation Works

### Sequence Detection

VimAbl uses a sequence detector to recognize multi-key commands like `gg`:

1. First `g` press starts a timer (500ms window)
2. Second `g` press triggers the command
3. If timeout expires, sequence is reset

### Automatic Scrolling

Unlike native Ableton commands, VimAbl's navigation includes automatic scrolling:

- **Session View**: Ensures the selected scene is visible
- **Arrangement View**: Scrolls the track list to show the selected track

This provides a more complete "jump" behavior similar to Vim's `gg` and `G`.

### Context Awareness

Navigation commands automatically detect which view is active:

```lua
-- Pseudo-code showing context detection
if currentView == "session" then
    selectFirstScene()
else
    selectFirstTrack()
end
```

## Advanced Usage

### Quick Scene/Track Navigation

Combine `gg` and `G` for quick navigation patterns:

**Pattern 1: Review project structure**
```
gg → G → gg → G
(Top → Bottom → Top → Bottom)
```

**Pattern 2: Navigate to specific area**
```
gg → (arrow keys to desired location)
(Start at top, navigate with arrows)
```

### Integration with Native Navigation

VimAbl commands work alongside Ableton's native navigation:

- **Arrow keys** - Move one scene/track at a time
- **Page Up/Down** - Move page by page
- **VimAbl `gg`/`G`** - Jump to extremes

## Performance

Navigation commands are optimized for speed:

| Metric | Value |
|--------|-------|
| Command latency | 20-50ms |
| Scroll smoothness | Native Ableton |
| CPU usage | < 1% |

## Troubleshooting

### `gg` Not Working

**Symptom:** Pressing `g` twice doesn't jump

**Solutions:**
1. ✅ Press `g` twice within 500ms
2. ✅ Ensure Ableton Live is frontmost app
3. ✅ Check Hammerspoon console for errors
4. ✅ Verify eventtap is running (auto-restarts every 5s)

### Navigation Jumps to Wrong Location

**Symptom:** Command selects unexpected scene/track

**Solutions:**
1. ✅ Check which view is active (Session vs Arrangement)
2. ✅ Verify server connection: `echo "GET_VIEW" | nc 127.0.0.1 9001`
3. ✅ Restart Ableton Live to reload Remote Script

### Scrolling Doesn't Work

**Symptom:** Selection changes but view doesn't scroll

**Solutions:**
1. ✅ This is expected in some Ableton versions (API limitation)
2. ✅ Try using native Ableton scrolling after selection
3. ✅ Check Remote Script log for errors

## See Also

- [Editing Commands](editing.md) - Modify your project
- [Keybindings Reference](keybindings.md) - Complete command list
- [Session vs Arrangement](session-vs-arrangement.md) - View-specific behavior
