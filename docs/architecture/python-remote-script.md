# Python Remote Script

The VimAbl Python Remote Script runs inside Ableton Live and provides the bridge between Live's internal state and external integrations (Hammerspoon, WebSocket, UDP/OSC).

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         Ableton Live Process                    │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  LiveState (ControlSurface)              │  │
│  │  • Main event loop (~60Hz)               │  │
│  │  • Logging infrastructure                │  │
│  │  • Component lifecycle management        │  │
│  └──────────────────────────────────────────┘  │
│           │         │           │               │
│           ▼         ▼           ▼               │
│  ┌───────────┐ ┌─────────┐ ┌──────────────┐   │
│  │ Observers │ │  UDP    │ │   Command    │   │
│  │  Manager  │ │ Sender  │ │   Server     │   │
│  └───────────┘ └─────────┘ └──────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    (UDP/OSC)    (UDP/OSC Events) (TCP Socket)
```

## Logging System

### Architecture

VimAbl uses a **thread-safe, queue-based logging system** optimized for Ableton Live's constraints:

- **Zero Live API calls from background threads** - Only the main thread calls `ControlSurface.log_message()`
- **Tuple-based queueing** - Formatting deferred to main thread for speed
- **Adaptive queue draining** - Automatically increases drain rate when backlog builds
- **Severity level filtering** - DEBUG, INFO, WARN, ERROR, CRITICAL
- **Performance metrics** - Real-time tracking with <0.1% overhead

### Key Components

#### `logging_config.py`

Core logging infrastructure:

```python
# Producer side (any thread)
log(component: str, message: str, level: str = "INFO", force: bool = False)

# Consumer side (main thread only)
init_logging(log_callback)      # Initialize on startup
drain_log_queue(max_messages)   # Drain in update_display()
clear_log_queue()                # Clear on shutdown

# Performance monitoring
get_log_stats() -> dict          # Get metrics
reset_log_stats()                # Reset counters
```

#### Configuration

```python
# Global settings (logging_config.py)
ENABLE_LOGGING = True            # Toggle all logging
ENABLED_LEVELS = {"INFO", "WARN", "ERROR", "CRITICAL"}
```

### Thread Safety

The logging system handles cross-thread communication safely:

1. **Background threads** (UDP, observers) → Call `log()` → Messages queued
2. **Main thread** (60Hz) → Calls `drain_log_queue()` → Messages written via `ControlSurface.log_message()`
3. **No locks required** - Python's `Queue` is thread-safe

### Performance Metrics

Automatically tracked with negligible overhead:

| Metric | Type | Description |
|--------|------|-------------|
| `messages_enqueued` | Counter | Total messages sent to queue |
| `messages_drained` | Counter | Messages successfully logged |
| `messages_dropped` | Counter | Messages lost (queue full) |
| `peak_queue_size` | Gauge | Highest queue depth |
| `queue_utilization` | Percentage | Current queue capacity used |
| `drop_rate` | Percentage | Message loss rate |

See [Performance Tuning](../development/performance-tuning.md) for details.

## Observer System

### ObserverManager

Manages all Live API observers:

- **TrackObserver** - Per-track state (name, mute, arm, volume, devices, clip slots)
- **DeviceObserver** - Per-device parameters (debounced)
- **TransportObserver** - Global playback state (play, tempo)
- **SceneObserver** - Per-scene state (name, color, triggered)
- **SessionCursorObserver** - Session View cursor tracking

### Event Flow

```
Live API Change → Observer Callback → UDP Event → WebSocket Broadcast
                                  ↓
                            Log Message Queue
```

## UDP/OSC Event System

### UDPSender

Non-blocking UDP sender for real-time events:

- **Fire-and-forget** - Never blocks main thread
- **Sequenced messages** - Monotonic sequence numbers
- **Batching support** - Group related events
- **Error resilient** - Logs failures but continues

See [OSC Protocol](../api-reference/osc-protocol.md) for event format.

## Command Server

TCP socket server for bidirectional communication:

- **Port 9001** - Accepts commands from Hammerspoon
- **Async I/O** - Non-blocking socket operations
- **JSON protocol** - Structured command/response format

See [Commands API](../api-reference/commands.md) for available commands.

## Lifecycle

```python
# Startup (Ableton loads script)
LiveState.__init__()
  ├─ init_logging(self.log_message)
  ├─ UDPSender.start()
  ├─ ObserverManager.start()
  └─ CommandServer.start()

# Main loop (~60Hz)
LiveState.update_display()
  ├─ drain_log_queue()              # Process logs
  ├─ ObserverManager.update()       # Debounce checks
  └─ SessionCursorObserver.update() # Cursor polling

# Shutdown (Ableton unloads script)
LiveState.disconnect()
  ├─ ObserverManager.stop()
  ├─ UDPSender.stop()
  ├─ CommandServer.stop()
  ├─ get_log_stats() → Log final metrics
  └─ drain_log_queue() → Flush remaining logs
```

## File Structure

```
src/remote_script/
├── __init__.py                  # Package initialization
├── LiveState.py                 # Main ControlSurface class
├── logging_config.py            # Centralized logging system
├── observers.py                 # Observer implementations
├── cursor_observer.py           # Session View cursor tracking
├── udp_sender.py                # UDP/OSC event sender
├── osc.py                       # OSC message encoding
├── commands.py                  # Command handlers
├── server.py                    # TCP command server
├── debounce.py                  # Event debouncing
└── _Framework/                  # Ableton's Remote Script framework
```

## Best Practices

### Logging

```python
# ✅ Good - Explicit severity levels
log("Component", "Started successfully", level="INFO")
log("Component", "Invalid state detected", level="WARN")
log("Component", "Critical failure", level="ERROR", force=True)

# ❌ Bad - Logging in hot paths without level filtering
for i in range(1000):
    log("HotPath", f"Processing {i}")  # Spams logs!

# ✅ Good - Use appropriate levels and force flag
log("Init", "System starting", level="INFO")      # Normal operation
log("Debug", "Value: {x}", level="DEBUG")         # Filtered out by default
log("Critical", "System crash", level="CRITICAL", force=True)  # Always logged
```

### Observer Callbacks

```python
# ✅ Good - Non-blocking, just set flags
def _on_name_changed(self):
    self._name_changed = True

# ❌ Bad - Heavy work in callback
def _on_name_changed(self):
    self.log("Long message...")      # String formatting
    self.send_event(...)             # Network I/O
    self.update_database(...)        # Database write
```

### Error Handling

```python
# ✅ Good - Graceful degradation
try:
    risky_operation()
except Exception as e:
    log("Component", f"Operation failed: {e}", level="ERROR")
    # Continue with degraded functionality

# ❌ Bad - Crash on error
risky_operation()  # Uncaught exception crashes script
```

## Debugging

### Viewing Logs

Ableton Live logs to:
- **macOS**: `~/Library/Preferences/Ableton/Live {version}/Log.txt`
- **Windows**: `%APPDATA%\Ableton\Live {version}\Preferences\Log.txt`

### Live Reload

After editing Remote Script code:
1. Go to Live Preferences → Link/Tempo/MIDI
2. Change Control Surface to "None"
3. Change back to "VimAbl"
4. Script reloads without restarting Ableton

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No logs appearing | `ENABLE_LOGGING = False` | Set to `True` in `logging_config.py` |
| High drop rate | Excessive logging | Reduce `ENABLED_LEVELS`, disable DEBUG |
| Observer not firing | Listener not registered | Check `_add_listeners()` called |
| UDP events not sent | Sender not started | Check `UDPSender.start()` called |

See [Troubleshooting](../troubleshooting.md) for more details.
