# Logging API Reference

VimAbl's centralized logging system provides thread-safe logging with performance metrics tracking.

## Core Functions

### `log()`

```python
def log(component: str, message: str, level: str = "INFO", force: bool = False) -> None
```

Thread-safe logging function callable from any thread.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `component` | `str` | *required* | Component name (e.g., "UDPSender", "TrackObserver") |
| `message` | `str` | *required* | Log message text |
| `level` | `str` | `"INFO"` | Severity level: `"DEBUG"`, `"INFO"`, `"WARN"`, `"ERROR"`, `"CRITICAL"` |
| `force` | `bool` | `False` | If `True`, log even when `ENABLE_LOGGING = False` |

**Returns:** `None`

**Example:**

```python
from .logging_config import log

# Basic usage
log("MyComponent", "Operation completed")

# With explicit level
log("MyComponent", "Starting initialization", level="INFO")
log("MyComponent", "Deprecated API used", level="WARN")
log("MyComponent", "Failed to connect", level="ERROR")

# Force critical errors to always log
log("MyComponent", "System crash detected", level="CRITICAL", force=True)
```

**Thread Safety:** Fully thread-safe. Safe to call from background threads.

**Performance:** O(1) - Negligible overhead (<1μs per call)

---

### `init_logging()`

```python
def init_logging(log_callback: Callable[[str], None]) -> None
```

Initialize the logging system. **Must be called once** from the main thread during startup.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `log_callback` | `Callable[[str], None]` | Reference to `ControlSurface.log_message` |

**Returns:** `None`

**Example:**

```python
from .logging_config import init_logging

class LiveState(ControlSurface):
    def __init__(self, c_instance):
        super().__init__(c_instance)

        # Initialize logging FIRST
        init_logging(self.log_message)
```

**Side Effects:**
- Sets global `_log_callback`
- Resets all performance metrics to zero

**Thread Safety:** Main thread only

---

### `drain_log_queue()`

```python
def drain_log_queue(max_messages: int = 200) -> None
```

Drain pending log messages from queue and write to Ableton's log. **Must be called** periodically from the main thread (typically in `update_display()`).

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_messages` | `int` | `200` | Base limit for messages to drain per call |

**Returns:** `None`

**Adaptive Draining:**

The actual drain limit is `max(max_messages, queue_size // 2)`, meaning:
- Small backlog → drains up to `max_messages`
- Large backlog → drains more aggressively to catch up

**Example:**

```python
from .logging_config import drain_log_queue

class LiveState(ControlSurface):
    def update_display(self):
        super().update_display()

        # Drain log queue (~60Hz)
        drain_log_queue()
```

**Performance:** O(n) where n = number of messages drained

**Thread Safety:** Main thread only

---

### `clear_log_queue()`

```python
def clear_log_queue() -> None
```

Clear all pending messages from the queue without logging them. Typically called during shutdown.

**Parameters:** None

**Returns:** `None`

**Example:**

```python
from .logging_config import drain_log_queue, clear_log_queue

class LiveState(ControlSurface):
    def disconnect(self):
        # Drain remaining messages
        drain_log_queue(max_messages=1000)

        # Clear any stragglers
        clear_log_queue()
```

**Thread Safety:** Main thread only

---

## Performance Metrics

### `get_log_stats()`

```python
def get_log_stats() -> dict
```

Get current logging performance metrics.

**Parameters:** None

**Returns:** `dict` with the following keys:

| Key | Type | Description |
|-----|------|-------------|
| `queue_size` | `int` | Current number of messages in queue |
| `queue_max` | `int` | Maximum queue capacity (2000) |
| `queue_utilization` | `float` | Queue usage percentage (0-100) |
| `messages_enqueued` | `int` | Total messages sent to queue since startup |
| `messages_dropped` | `int` | Messages lost due to full queue |
| `messages_drained` | `int` | Messages successfully written to log |
| `peak_queue_size` | `int` | Highest queue size reached |
| `drop_rate` | `float` | Percentage of messages dropped (0-100) |

**Example:**

```python
from .logging_config import get_log_stats, log

stats = get_log_stats()

# Log periodic stats
log("Monitor",
    f"Logging health: {stats['messages_drained']} drained, "
    f"{stats['messages_dropped']} dropped ({stats['drop_rate']}%), "
    f"peak: {stats['peak_queue_size']}/{stats['queue_max']}",
    level="INFO")

# Alert on high drop rate
if stats['drop_rate'] > 1.0:
    log("Monitor",
        f"High message drop rate: {stats['drop_rate']}%",
        level="WARN")

# Alert on queue pressure
if stats['queue_utilization'] > 80:
    log("Monitor",
        f"Queue near capacity: {stats['queue_utilization']}%",
        level="WARN")
```

**Performance:** O(1) - Fast snapshot

**Thread Safety:** Thread-safe (read-only access to atomic counters)

---

### `reset_log_stats()`

```python
def reset_log_stats() -> None
```

Reset all performance metric counters to zero.

**Parameters:** None

**Returns:** `None`

**Example:**

```python
from .logging_config import reset_log_stats, get_log_stats

# Get stats before reset
old_stats = get_log_stats()

# Reset counters
reset_log_stats()

# Get fresh stats
new_stats = get_log_stats()
assert new_stats['messages_enqueued'] == 0
```

**Thread Safety:** Main thread only (modifies global counters)

---

## Configuration

### Global Settings

Edit `src/remote_script/logging_config.py`:

```python
# Enable/disable all logging
ENABLE_LOGGING = True  # Set to False for production

# Filter by severity level
ENABLED_LEVELS = {"INFO", "WARN", "ERROR", "CRITICAL"}
```

### Severity Levels

| Level | Priority | Use Case | Filtered by Default |
|-------|----------|----------|---------------------|
| `DEBUG` | 0 | Verbose debugging info | ✅ Yes |
| `INFO` | 1 | Normal operation events | ❌ No |
| `WARN` | 2 | Warnings, degraded state | ❌ No |
| `ERROR` | 3 | Errors, failures | ❌ No |
| `CRITICAL` | 4 | System crashes, fatal errors | ❌ No |

**Note:** Messages with `force=True` bypass level filtering.

---

## Performance Characteristics

| Operation | Complexity | Overhead | Thread-Safe |
|-----------|------------|----------|-------------|
| `log()` | O(1) | <1μs | ✅ Yes |
| `drain_log_queue()` | O(n) | ~50μs/msg | ❌ No (main thread only) |
| `get_log_stats()` | O(1) | <1μs | ✅ Yes |
| Metrics tracking | O(1) | <0.1% CPU | ✅ Yes |

**Queue Capacity:** 2000 messages

**Drain Rate:** 200-1000 messages per update (~60Hz) depending on backlog

**Memory Usage:** ~100 bytes per queued message

---

## Best Practices

### ✅ Do

```python
# Use appropriate severity levels
log("Init", "System starting", level="INFO")
log("Validator", "Invalid input detected", level="WARN")
log("Database", "Connection failed", level="ERROR")

# Force critical errors
log("System", "Unrecoverable error", level="CRITICAL", force=True)

# Check metrics periodically
stats = get_log_stats()
if stats['drop_rate'] > 1.0:
    # Reduce logging or increase drain rate
    pass
```

### ❌ Don't

```python
# Don't log in tight loops without level control
for i in range(10000):
    log("Loop", f"Processing {i}")  # Spams queue!

# Don't call drain_log_queue() from background threads
def background_thread():
    drain_log_queue()  # UNSAFE! Main thread only!

# Don't format expensive strings unconditionally
log("Debug", f"Expensive: {compute_expensive_thing()}")  # Still computes if filtered!

# Better: Use level filtering
if "DEBUG" in ENABLED_LEVELS:
    log("Debug", f"Expensive: {compute_expensive_thing()}", level="DEBUG")
```

---

## Health Monitoring

### Interpreting Metrics

**Healthy System:**
```python
{
    "queue_size": 5,
    "queue_utilization": 0.25,
    "drop_rate": 0.0,
    "peak_queue_size": 45
}
```

**Warning Signs:**
```python
{
    "queue_size": 1500,
    "queue_utilization": 75.0,
    "drop_rate": 0.5,
    "peak_queue_size": 1800
}
# Action: Reduce log volume or increase drain rate
```

**Critical Issues:**
```python
{
    "queue_size": 2000,
    "queue_utilization": 100.0,
    "drop_rate": 5.2,
    "peak_queue_size": 2000
}
# Action: Disable non-critical logging immediately
```

### Automatic Monitoring

VimAbl logs stats automatically:
- **Every 5 minutes** during operation
- **On shutdown** (final metrics)

Example log output:
```
[12:34:56.789] [INFO] [LiveState] Logging stats: 12450 drained, 0 dropped (0.0%), peak queue: 45/2000
```

---

## See Also

- [Performance Tuning](../development/performance-tuning.md) - Logging optimization guide
- [Python Remote Script](../architecture/python-remote-script.md) - Overall architecture
- [Troubleshooting](../troubleshooting.md) - Common logging issues
