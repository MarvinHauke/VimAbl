# Ableton Live API References

## Official Documentation

### Live Object Model (LOM) Documentation

**URL**: https://docs.cycling74.com/apiref/lom/

**What it is**: Official Cycling '74 documentation for the Ableton Live Object Model (LOM). This is the Python API that runs inside Ableton Live and is accessible from Remote Scripts.

**Key Objects**:

- **Application**: The Live application (`live_app`)
- **Song**: Represents a Live Set (the main document)
- **Track**: Audio/MIDI tracks
- **Device**: Audio effects, MIDI effects, instruments
- **Clip**: Audio or MIDI clips in Session view
- **Scene**: Horizontal rows in Session view

**Important Notes**:

- This is the authoritative source for Live's Python API
- Use this to understand what properties and methods are available
- The API is exposed through Max for Live but also accessible in Remote Scripts

### Common API Patterns

```python
# Get the song (Live Set)
song = self.song()

# Access properties
is_playing = song.is_playing
current_tempo = song.tempo

# Get tracks
tracks = song.tracks  # Returns list of Track objects

# Get scenes
scenes = song.scenes  # Returns list of Scene objects

# Get current view
view = song.view
selected_track = view.selected_track
```

## Unofficial Decompiled Sources

### Ableton Live 11 MIDI Remote Scripts

**URL**: https://github.com/gluon/AbletonLive11_MIDIRemoteScripts

### Ableton Live 12 MIDI Remote Scripts

**URL**: https://github.com/gluon/AbletonLive12_MIDIRemoteScripts

**What it is**: Decompiled Python source code of Ableton Live 11's built-in MIDI Remote Scripts. This is an unofficial repository that shows how Ableton's own controllers are implemented.

**Why it's useful**:

- Shows real-world examples of Remote Script patterns
- Demonstrates how to use the `_Framework` module
- Contains implementations for Push, APC40, Launchpad, etc.
- Helps understand threading, observers, and component architecture

**Key Directories**:

- `_Framework/` - Core framework classes (ControlSurface, ComponentBase, etc.)
- `Push/` - Push 1 controller implementation
- `Push2/` - Push 2 controller implementation
- `APC40/` - Akai APC40 implementation
- Other controller-specific folders

**IMPORTANT**:

- This is DECOMPILED code (not official)
- Repo states "NO support given, ONLY source files!"
- Use for reference and learning, not as official documentation
- May contain decompilation artifacts or inaccuracies

### Example Patterns from Decompiled Scripts

#### Thread-Safe Command Execution

```python
# Commands that access song() must be scheduled
def some_command(self):
    self.schedule_message(1, self._do_command)

def _do_command(self):
    # Now safe to access self.song()
    track = self.song().view.selected_track
```

#### Observer Pattern

```python
# Add listener for property changes
def add_listeners(self):
    song = self.song()
    song.add_is_playing_listener(self._on_playing_changed)

def _on_playing_changed(self):
    is_playing = self.song().is_playing
    # React to change
```

#### Component Architecture

```python
# Framework's component-based approach
class MyComponent(Component):
    def __init__(self):
        super().__init__()
        # Component setup

    def update(self):
        # Update component state
```

## Important API Limitations

### Document Path

**Issue**: There is NO reliable `document.path` property in the Live API!

**What we tried**:

1. `application.get_document().path` - Returns None
2. `song().canonical_parent.canonical_parent` - Returns None
3. `song().path` - Doesn't exist

**Solution**: Pass the path from outside Ableton (e.g., from file watcher)

### XML Export

**Issue**: There is NO `song().save_as_xml()` method!

**What we learned**:

- .als files are just gzipped XML
- No Live API needed for XML extraction
- Can decompress directly with Python's `gzip` module

**Solution**:

```python
import gzip
with gzip.open(project_path, 'rb') as f_in:
    with open(xml_path, 'wb') as f_out:
        f_out.write(f_in.read())
```

## Remote Script Framework Basics

### ControlSurface Base Class

All Remote Scripts inherit from `_Framework.ControlSurface`:

```python
from _Framework.ControlSurface import ControlSurface

class MyScript(ControlSurface):
    def __init__(self, c_instance):
        super().__init__(c_instance)
        self.show_message("Script loaded")

    def disconnect(self):
        super().disconnect()

    def song(self):
        # Access to the Song object
        return super().song()
```

### Key Methods

#### `schedule_message(delay, callback)`

Schedules a callback to run in Live's main thread after delay (in ticks).
Use this for ANY operation that accesses `song()`.

#### `show_message(text)`

Shows a message in Live's status bar.

#### `log_message(text)`

Writes to Live's Log.txt file.

#### `song()`

Returns the current Song object. MUST be called from main thread!

### Threading Rules

- Remote Scripts run in a separate thread
- Live's API is NOT thread-safe
- Always use `schedule_message()` for song() access
- Only direct commands (like `GET_VIEW` checking a flag) can skip scheduling

## Socket Server Protocol (Our Implementation)

### Format

Colon-delimited: `COMMAND:param1:param2:param3`

### Parsing (server.py:97)

```python
parts = request.split(':')
command = parts[0]          # The command name
params = parts[1:]          # List of parameters (or None)
```

### Response

Always JSON:

```python
response = json.dumps({
    "success": True/False,
    "data": {...},
    "error": "..." if failed
})
```

## Version Compatibility

### Our Setup

- Ableton Live 12.3 beta 16
- Python 3.11/3.13 compatible
- macOS (Darwin 24.6.0)

### API Changes Across Versions

- Live 11 → Live 12: Minor changes, mostly compatible
- Some properties added/removed between versions
- Beta versions may have unstable APIs
- Always test after Live updates!

## Best Practices

1. **Always wrap song() calls**: Use `schedule_message()` or `try-except`
2. **Check attribute existence**: Use `hasattr()` before accessing
3. **Handle None values**: Many API calls can return None
4. **Log extensively**: Use `log_message()` for debugging
5. **Test with real hardware**: Virtual MIDI can behave differently
6. **Clean up listeners**: Remove all listeners in `disconnect()`
7. **Avoid tight loops**: Can freeze Live's UI
8. **Don't assume paths exist**: Check file system before operations

## Debugging Tools

### Live's Log File

```bash
# Live 12.x
tail -f ~/Library/Preferences/Ableton/Live\ 12.*/Log.txt

# Shows:
# - Remote Script load/unload
# - Python errors
# - log_message() output
# - API warnings
```

### Python REPL in Max for Live

Can test Live API interactively, but:

- Different threading model than Remote Scripts
- Some APIs only available in Remote Scripts
- Useful for exploring object properties

### Remote Script Console

Our implementation logs to both:

1. Live's Log.txt
2. Hammerspoon console (via socket responses)

## Related Documentation Links

- **Max for Live API**: Similar to Remote Script API but with differences
- **Structure Void's LOM docs**: https://structure-void.com/PythonLiveAPI_documentation/Live11.0.xml
- **Ableton Forum**: https://forum.ableton.com/viewforum.php?f=1 (Python/Remote Scripts section)

## Common Gotchas

1. **No file path access**: Can't reliably get current project path from Live API
2. **No XML export**: Can't export project as XML via API
3. **Threading is strict**: Any song() call must be scheduled
4. **Listeners accumulate**: Must remove in disconnect() or memory leaks
5. **API is read-mostly**: Can't create tracks/devices via API in most cases
6. **Beta versions**: API may change between beta releases
7. **MIDI required**: Remote Scripts need MIDI port (even if unused)

## Our Custom Extensions

Since the Live API is limited, we've added:

1. **External path passing**: File watcher sends .als path via socket
2. **Direct XML extraction**: Decompress .als files without Live API
3. **WebSocket server**: Separate process for real-time visualization
4. **Smart caching**: Only re-export XML when .als changes

These work AROUND the API limitations rather than fighting them!
