# Session vs Arrangement View

Understanding how VimAbl commands behave differently in each Ableton Live view.

## View Detection

VimAbl automatically detects which view is active and adjusts command behavior accordingly.

### How It Works

The Remote Script monitors Live's view state:

```python
# View detection in Remote Script
current_view = self.application().view.focused_document_view
# Returns: "Session" or "Arrangement"
```

Commands query this state before executing:

```bash
echo "GET_VIEW" | nc 127.0.0.1 9001
# Returns: {"view": "session"} or {"view": "arrangement"}
```

## Session View Commands

### Navigation

| Command | Action |
|---------|--------|
| `gg` | Select first scene, scroll to top |
| `G` | Select last scene, scroll to bottom |

### Editing

| Command | Action |
|---------|--------|
| `dd` | Delete selected scene or clip |
| `za` | Undo last operation |

### Use Cases

Session View is optimized for:
- Live performance and improvisation
- Clip-based composition
- Scene arrangement and triggering

## Arrangement View Commands

### Navigation

| Command | Action |
|---------|--------|
| `gg` | Select first track, scroll track list to top |
| `G` | Select last track, scroll track list to bottom |

### Editing

| Command | Action |
|---------|--------|
| `dd` | Delete selected track or clip |
| `za` | Undo last operation |

### Use Cases

Arrangement View is optimized for:
- Linear composition and editing
- Timeline-based production
- Final arrangement and mixdown

## Shared Commands

Some commands work identically in both views:

### Browser Control

| Command | Action |
|---------|--------|
| `Ctrl + -` | Toggle device browser |

### System Commands

All system-level commands (observer control, server status) work in any view.

## View Switching

### Native Ableton

Use Ableton's native view switching:
- **Tab** - Switch between Session and Arrangement
- **Cmd+Tab** - Application switcher (macOS)

### VimAbl Integration

VimAbl commands automatically adapt when you switch views - no configuration needed!

```
Session View → Press gg → Jumps to first scene
Switch to Arrangement View (Tab)
Arrangement View → Press gg → Jumps to first track
```

## Best Practices

### 1. Understand Your Workflow

**Session-focused workflow:**
- Ideal for live performance
- Use `gg`/`G` for quick scene navigation
- Organize scenes logically (intro, verse, chorus, etc.)

**Arrangement-focused workflow:**
- Ideal for production
- Use `gg`/`G` for track navigation
- Organize tracks by type (drums, bass, synths, etc.)

### 2. Leverage Context Awareness

Don't try to remember different keybindings for each view - VimAbl does the right thing automatically:

```
Same muscle memory → Different context → Appropriate action
```

### 3. Combine with Native Navigation

VimAbl's `gg`/`G` work great with Ableton's native navigation:

- `gg` → Jump to start
- Arrow keys → Navigate to specific location
- `G` → Jump to end for comparison

## Implementation Details

### View State Caching

For performance, VimAbl caches the current view state:

- View changes are monitored via Live API observer
- Cache is updated immediately on view switch
- Fast path for `GET_VIEW` command (no thread switching)

### Command Routing

Commands are routed based on view:

```python
def handle_select_first(self):
    view = self.get_current_view()
    if view == "session":
        self.select_first_scene()
    else:
        self.select_first_track()
```

## Future Enhancements

!!! info "Planned Features"
    - **Detail View awareness** - Different commands for detail panel
    - **Browser navigation** - Vim-style browsing in device browser
    - **Mixer View support** - Dedicated commands for mixer view

## Troubleshooting

### Command Does Wrong Action

**Symptom:** `gg` jumps to wrong thing

**Solution:**
```bash
# Check current view
echo "GET_VIEW" | nc 127.0.0.1 9001

# Verify it matches what you see in Ableton
```

### View Detection Not Working

**Symptom:** Commands always behave like Session view

**Solution:**
1. ✅ Restart Ableton Live
2. ✅ Check Remote Script log for errors
3. ✅ Verify Remote Script is properly installed

## See Also

- [Navigation](navigation.md) - Navigation commands
- [Editing](editing.md) - Editing commands
- [Keybindings Reference](keybindings.md) - Complete command list
