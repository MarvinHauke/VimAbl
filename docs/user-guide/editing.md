# Editing

Learn how to edit and manipulate your Ableton Live project using Vim-style commands.

## Core Editing Commands

### Delete: `dd`

The `dd` command (press `d` twice quickly) deletes the currently selected item:

**In Session View:**
- Deletes the selected **scene** or **clip**

**In Arrangement View:**
- Deletes the selected **track** or **clip**

**Usage:**
```
Press: d d (within 500ms)
```

!!! warning "Destructive Operation"
    Delete cannot be undone in some cases. Use `za` to undo if needed.

### Undo: `za`

The `za` command triggers Ableton's undo function:

**In Any View:**
- Undoes the last operation
- Works with both VimAbl commands and native Ableton edits

**Usage:**
```
Press: z a
```

!!! tip "Vim Mapping"
    In Vim, `za` toggles folds. VimAbl repurposes this for undo since Ableton doesn't have code folding.

## View Controls

### Toggle Browser: `Ctrl + -`

Toggles the Ableton device browser open/closed:

**Usage:**
```
Press: Ctrl + - (hyphen/minus)
```

**Use Cases:**
- Quick access to devices and instruments
- Close browser to maximize screen space
- Navigate browser with keyboard after opening

## How Editing Works

### Double-Tap Detection

Edit commands like `dd` use the same sequence detector as navigation:

1. First `d` press starts a timer (500ms window)
2. Second `d` press triggers delete
3. If timeout expires, sequence is reset

### Thread Safety

All editing commands are executed on Ableton's main thread:

```python
# Pseudo-code showing thread-safe execution
def handle_delete():
    schedule_message(0, self._do_delete)  # Execute on main thread
```

This ensures stability and prevents crashes.

### Undo Integration

VimAbl's undo command (`za`) calls Ableton's native undo:

```python
def handle_undo():
    song = self.song()
    song.undo()
```

This integrates seamlessly with Ableton's undo history.

## Advanced Usage

### Quick Edit Patterns

**Pattern 1: Delete and undo review**
```
dd → (review result) → za (if mistake)
```

**Pattern 2: Clean up project**
```
gg → (review scenes) → dd → dd → dd (delete multiple)
```

**Pattern 3: Browser workflow**
```
Ctrl + - → (select device) → Enter → Ctrl + -
(Open browser → choose → close browser)
```

## Planned Features

!!! info "Coming Soon"
    These editing features are planned for future releases:

    - **`y` (yank)** - Copy selected item
    - **`p` (put)** - Paste copied item
    - **`c` (change)** - Replace selected item
    - **Visual mode** - Select multiple items
    - **`u` (undo)** - Direct undo (not `za`)
    - **`Ctrl+r` (redo)** - Redo last undone operation

## Performance

Editing commands are fast and reliable:

| Metric | Value |
|--------|-------|
| Command latency | 20-50ms |
| Thread safety | ✅ All commands |
| Undo integration | ✅ Native |

## Troubleshooting

### `dd` Not Deleting

**Symptom:** Pressing `d` twice doesn't delete

**Solutions:**
1. ✅ Press `d` twice within 500ms
2. ✅ Ensure something is selected
3. ✅ Check Ableton Live is frontmost app
4. ✅ Verify Remote Script is running

### Undo (`za`) Not Working

**Symptom:** Nothing happens when pressing `z` then `a`

**Solutions:**
1. ✅ Ensure there's something to undo
2. ✅ Check Hammerspoon console for errors
3. ✅ Test with native undo (Cmd+Z) to verify it works
4. ✅ Restart Hammerspoon

### Browser Toggle Not Responding

**Symptom:** `Ctrl + -` doesn't toggle browser

**Solutions:**
1. ✅ Verify keybinding isn't conflicting with other apps
2. ✅ Check Hammerspoon eventtap is running
3. ✅ Try reloading Hammerspoon config
4. ✅ Check for macOS accessibility permissions

## See Also

- [Navigation Commands](navigation.md) - Move around efficiently
- [Keybindings Reference](keybindings.md) - Complete command list
- [Session vs Arrangement](session-vs-arrangement.md) - View-specific behavior
