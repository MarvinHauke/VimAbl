# Performance Tuning

VimAbl includes several performance optimizations, with the most significant being **configurable logging**.

## Logging Configuration

### Overview

Logging has a **~10-20% CPU overhead** in Python Remote Scripts running in Ableton Live. For production use or when experiencing performance issues, you can disable logging globally.

**Performance metrics tracking** adds negligible overhead (<0.1%) and remains active even when logging is disabled, allowing you to monitor system health.

### How to Toggle Logging

Edit `src/remote_script/logging_config.py`:

```python
# Set to False to disable all logging for better performance
# Critical errors will still be logged
ENABLE_LOGGING = False  # Change to False for production
```

### What Gets Logged

When `ENABLE_LOGGING = True` (development mode):
- All observer events (track selection, clip slot changes, etc.)
- UDP/OSC event sends
- Cursor tracking events
- Document path changes
- Initialization and cleanup messages

When `ENABLE_LOGGING = False` (production mode):
- **Only critical errors** (force=True parameter)
- System failures
- Observer initialization failures
- UDP sender errors

### Performance Impact

| Setting | CPU Usage | Log File Size | Metrics Overhead | Recommended For |
|---------|-----------|---------------|------------------|-----------------|
| `ENABLE_LOGGING = True` | Baseline | Large (~MB/session) | <0.1% | Development, debugging |
| `ENABLE_LOGGING = False` | **10-20% reduction** | Minimal (~KB/session) | <0.1% | Production, performance-critical setups |

**Why metrics have minimal overhead:**
- Integer counter increments (nanosecond operations)
- No string formatting or memory allocation
- Atomic operations (no locking required)
- Queue size check reuses existing `qsize()` call

The benefits of performance monitoring far outweigh the negligible CPU cost.

### Files Using Centralized Logging

All Python Remote Script files use the centralized logging configuration:

- `src/remote_script/observers.py` - Track/Device/Transport observers
- `src/remote_script/udp_sender.py` - UDP event sender
- `src/remote_script/cursor_observer.py` - Session view cursor tracking
- `src/remote_script/LiveState.py` - Main Remote Script controller

### Performance Metrics

VimAbl automatically tracks logging performance with negligible overhead (<0.1% CPU). Metrics are logged every 5 minutes and on shutdown.

**Available Metrics:**

| Metric | Description | What It Means |
|--------|-------------|---------------|
| `messages_enqueued` | Total messages sent to queue | Overall logging activity |
| `messages_drained` | Messages written to log file | Successfully processed logs |
| `messages_dropped` | Messages lost (queue full) | System overload indicator |
| `drop_rate` | Percentage of dropped messages | Health metric (should be <1%) |
| `queue_size` | Current messages in queue | Real-time backlog |
| `queue_utilization` | Queue capacity used (%) | Peak load indicator |
| `peak_queue_size` | Highest queue size reached | Burst detection |

**Example log output:**
```
[12:34:56.789] [INFO] [LiveState] Logging stats: 12450 drained, 0 dropped (0.0%), peak queue: 45/2000
```

**Health Indicators:**

- **Healthy**: `drop_rate = 0%`, `peak_queue_size < 500`
- **Warning**: `drop_rate < 1%`, `peak_queue_size < 1000`
- **Critical**: `drop_rate > 1%`, `queue_utilization > 80%`

If you see high drop rates, consider:
1. Reducing enabled log levels (disable DEBUG/INFO)
2. Increasing queue drain rate
3. Disabling logging entirely for production

**Accessing Metrics Programmatically:**

```python
from .logging_config import get_log_stats

stats = get_log_stats()
if stats['drop_rate'] > 1.0:
    # Take action: reduce logging, alert operator, etc.
    pass
```

## Other Performance Considerations

### Observer Frequency

Some observers run at high frequency (~60Hz):
- **Cursor polling** - Checks highlighted_clip_slot every frame
- **Debounce updates** - Trailing edge event processing
- **Transport events** - Playback position updates

### UDP Listener Queue Architecture

The UDP listener uses an **asyncio.Queue** to decouple packet reception from event processing, preventing packet loss during rapid event bursts.

**Architecture:**

```
UDP Socket (Port 9002)
    ↓
Receive Loop (non-blocking)
    ↓
Parse OSC Message
    ↓
Queue Event (put_nowait)
    ↓
[asyncio.Queue (1000 events)]
    ↓
Event Processor Task (concurrent)
    ↓
WebSocket Broadcast
```

**Key Benefits:**

1. **Zero Packet Loss**: Even with 55+ events in <1ms bursts
2. **Non-Blocking Reception**: Slow WebSocket broadcasts don't block UDP receives
3. **Concurrent Processing**: Event processor runs in parallel with UDP receiver
4. **Queue Statistics**: Tracks queue size, max capacity, overflow events

**Queue Configuration:**

```python
# src/udp_listener/listener.py
self._event_queue = asyncio.Queue(maxsize=1000)  # Adjust capacity if needed
```

**Monitoring Queue Health:**

```python
stats = listener.get_stats()
print(f"Queue size: {stats['queue_size']}")
print(f"Queue max: {stats['queue_max']}")
print(f"Packets dropped: {stats['packets_dropped']}")
```

**When Queue Overflows:**

- UDP packets are **dropped** at reception (prevents blocking)
- Logged as ERROR: `"Event queue full! Dropping event..."`
- Gap detection system alerts to missing sequence numbers
- Consider increasing queue size if this occurs frequently

**Performance Impact:**

- Queue overhead: **<1ms per event**
- Memory usage: **~100KB for 1000 events** (typical payloads)
- CPU: Minimal (async queue operations are highly optimized)

### UDP Overhead

UDP event sending is non-blocking and has minimal overhead (<0.5ms per event). However, high-frequency events (e.g., volume faders during mixing) can generate significant traffic.

**Debouncing Strategy:**

- Volume/device parameters: **50ms trailing edge**
- Tempo changes: **100ms trailing edge**
- Structural changes (name, mute, arm): **Immediate (0ms)**

This reduces event rate by **80-90%** during parameter sweeps while maintaining responsiveness.

**Tip**: The web UI filters transport/play events from console logging to reduce spam.

### Web UI Optimization

The Svelte frontend uses:
- Reactive state management ($state runes)
- Efficient diff-based AST updates
- Minimal CSS animations (blue selection box only)
- Debounced WebSocket message processing

## Troubleshooting Performance

If experiencing performance issues:

1. **Disable logging** - Set `ENABLE_LOGGING = False` in `logging_config.py`
2. **Check browser console** - Look for excessive WebSocket messages
3. **Monitor CPU** - Check Ableton Live's CPU meter
4. **Reduce open devices** - Close unused device chains to reduce observer load

## Benchmarks

Performance measurements on MacBook Pro M1:

| Configuration | CPU Usage | Latency (selection → UI) |
|---------------|-----------|-------------------------|
| Logging ON | 15-20% | <50ms |
| Logging OFF | **5-10%** | <50ms |

*Note: Latency is unaffected by logging since UDP sends are non-blocking.*
