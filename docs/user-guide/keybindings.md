# Keybindings Reference

Complete reference of all VimAbl keybindings.

!!! tip "Auto-Generated Content"
    This page will be auto-generated from source code in future versions.

## Navigation Commands

### Session View

| Keybinding | Command | Description |
|------------|---------|-------------|
| `gg` | Select First Scene | Jump to first scene and scroll to top |
| `Shift+G` | Select Last Scene | Jump to last scene and scroll to bottom |

### Arrangement View

| Keybinding | Command | Description |
|------------|---------|-------------|
| `gg` | Select First Track | Jump to first track and scroll to top |
| `Shift+G` | Select Last Track | Jump to last track and scroll to bottom |

## Editing Commands

### All Views

| Keybinding | Command | Description |
|------------|---------|-------------|
| `dd` | Delete | Delete selected scene, track, or clip |
| `za` | Undo | Undo last operation |
| `Ctrl+-` | Toggle Browser | Open/close device browser |

## Web TreeViewer Commands

| Keybinding | Command | Description |
|------------|---------|-------------|
| `Cmd+Shift+W` | Toggle Server | Start/stop WebSocket server |
| `Cmd+Shift+R` | Restart Server | Restart WebSocket server |
| `Cmd+Shift+I` | Server Info | Show server status |

## Sequence Detection

### Timing

All multi-key sequences (like `gg`, `dd`, `za`) must be completed within **500ms**.

### Configuration

The timeout can be adjusted in `src/hammerspoon/config.lua`:

```lua
M.timeouts = {
    doubleTap = 500,    -- milliseconds
    sequence = 500,     -- milliseconds
}
```

## Customization

### Adding New Keybindings

See the [Development Guide](../development/extending.md) for instructions on adding custom keybindings.

### Modifying Existing Keybindings

Edit the keybinding files in `src/hammerspoon/keys/`:

- `navigation.lua` - Navigation commands
- `editing.lua` - Editing commands
- `views.lua` - View and browser toggles

## Vim Comparison

### Implemented

| Vim | VimAbl | Description |
|-----|--------|-------------|
| `gg` | `gg` | Jump to beginning |
| `G` | `G` | Jump to end |
| `dd` | `dd` | Delete line/item |
| `za` | `za` | Toggle fold → Undo (adapted) |

### Planned

| Vim | VimAbl (planned) | Description |
|-----|------------------|-------------|
| `y` | `y` | Yank (copy) |
| `p` | `p` | Put (paste) |
| `c` | `c` | Change |
| `u` | `u` | Undo (direct) |
| `Ctrl+r` | `Ctrl+r` | Redo |
| `v` | `v` | Visual mode |
| `h/j/k/l` | `h/j/k/l` | Motion (arrow keys) |

## Command Categories

### High-Frequency Commands
Commands you'll use most often:
- `gg` / `G` - Navigation
- `dd` - Delete

### Low-Frequency Commands
Commands for specific tasks:
- `Ctrl+-` - Browser toggle
- `Cmd+Shift+W` - Server control

### System Commands
Commands for debugging and status:
- `Cmd+Shift+I` - Server info

## Keyboard Layout Considerations

VimAbl keybindings are designed for QWERTY keyboards. If using a different layout:

1. Keybindings are based on physical key positions
2. Some characters may differ on non-QWERTY layouts
3. See [Development Guide](../development/extending.md) for remapping

## Accessibility

All keybindings can be executed with one hand for accessibility:

- `gg` - One hand, two fingers
- `G` - One hand (Shift+g)
- `dd` - One hand, two fingers
- `za` - One hand, two fingers

## See Also

- [Navigation Guide](navigation.md) - Detailed navigation docs
- [Editing Guide](editing.md) - Detailed editing docs
- [Session vs Arrangement](session-vs-arrangement.md) - View-specific behavior
