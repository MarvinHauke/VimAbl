# Performance Tuning

VimAbl includes several performance optimizations, with the most significant being **configurable logging**.

## Logging Configuration

### Overview

Logging has a **~10-20% CPU overhead** in Python Remote Scripts running in Ableton Live. For production use or when experiencing performance issues, you can disable logging globally.

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

| Setting | CPU Usage | Log File Size | Recommended For |
|---------|-----------|---------------|-----------------|
| `ENABLE_LOGGING = True` | Baseline | Large (~MB/session) | Development, debugging |
| `ENABLE_LOGGING = False` | **10-20% reduction** | Minimal (~KB/session) | Production, performance-critical setups |

### Files Using Centralized Logging

All Python Remote Script files use the centralized logging configuration:

- `src/remote_script/observers.py` - Track/Device/Transport observers
- `src/remote_script/udp_sender.py` - UDP event sender
- `src/remote_script/cursor_observer.py` - Session view cursor tracking
- `src/remote_script/LiveState.py` - Main Remote Script controller

## Other Performance Considerations

### Observer Frequency

Some observers run at high frequency (~60Hz):
- **Cursor polling** - Checks highlighted_clip_slot every frame
- **Debounce updates** - Trailing edge event processing
- **Transport events** - Playback position updates

### UDP Overhead

UDP event sending is non-blocking and has minimal overhead (<0.5ms per event). However, high-frequency events (e.g., volume faders during mixing) can generate significant traffic.

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
