# Commands Reference

Complete reference of all TCP socket commands available via port 9001.

!!! tip "Auto-Generated Content"
    This page will be auto-generated from source code in future versions.

## Command Format

Commands are sent via TCP socket on port 9001:

```bash
echo "COMMAND_NAME" | nc 127.0.0.1 9001
```

Responses are JSON:

```json
{"success": true, "data": {...}}
// or
{"success": false, "error": "error message"}
```

## View Commands

### GET_VIEW

Get the current view (Session or Arrangement).

**Request:**
```bash
echo "GET_VIEW" | nc 127.0.0.1 9001
```

**Response:**
```json
{"view": "session"}
// or
{"view": "arrangement"}
```

**Performance:** Fast path (no thread switching)

---

### GET_STATE

Get full Live state including transport, view, and track information.

**Request:**
```bash
echo "GET_STATE" | nc 127.0.0.1 9001
```

**Response:**
```json
{
  "view": "session",
  "transport": {
    "is_playing": true,
    "tempo": 120.0,
    "time_signature": [4, 4]
  },
  "tracks": [...],
  "scenes": [...]
}
```

**Performance:** Runs on main thread (20-50ms)

---

## Navigation Commands

### SELECT_FIRST_SCENE

Select the first scene in Session View.

**Request:**
```bash
echo "SELECT_FIRST_SCENE" | nc 127.0.0.1 9001
```

**Response:**
```json
{"success": true, "scene_index": 0}
```

**Behavior:**
- Only works in Session View
- Scrolls view to show first scene

---

### SELECT_LAST_SCENE

Select the last scene in Session View.

**Request:**
```bash
echo "SELECT_LAST_SCENE" | nc 127.0.0.1 9001
```

**Response:**
```json
{"success": true, "scene_index": 7}
```

**Behavior:**
- Only works in Session View
- Scrolls view to show last scene

---

### SELECT_FIRST_TRACK

Select the first track.

**Request:**
```bash
echo "SELECT_FIRST_TRACK" | nc 127.0.0.1 9001
```

**Response:**
```json
{"success": true, "track_index": 0}
```

**Behavior:**
- Works in both Session and Arrangement View
- Scrolls track list to top
- Selects first non-master track

---

### SELECT_LAST_TRACK

Select the last track.

**Request:**
```bash
echo "SELECT_LAST_TRACK" | nc 127.0.0.1 9001
```

**Response:**
```json
{"success": true, "track_index": 15}
```

**Behavior:**
- Works in both Session and Arrangement View
- Scrolls track list to bottom
- Selects last track before Master

---

## Observer Commands

### GET_OBSERVER_STATUS

Get statistics about active UDP/OSC observers.

**Request:**
```bash
echo "GET_OBSERVER_STATUS" | nc localhost 9001
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "track_observers": 16,
    "device_observers": 24,
    "total_events_sent": 1523,
    "uptime_seconds": 3600
  }
}
```

---

### START_OBSERVERS

Start all UDP/OSC observers (if stopped).

**Request:**
```bash
echo "START_OBSERVERS" | nc localhost 9001
```

**Response:**
```json
{"success": true, "message": "Observers started"}
```

---

### STOP_OBSERVERS

Stop all UDP/OSC observers (saves CPU).

**Request:**
```bash
echo "STOP_OBSERVERS" | nc localhost 9001
```

**Response:**
```json
{"success": true, "message": "Observers stopped"}
```

---

### REFRESH_OBSERVERS

Refresh observer list (useful after adding/removing tracks).

**Request:**
```bash
echo "REFRESH_OBSERVERS" | nc localhost 9001
```

**Response:**
```json
{"success": true, "message": "Observers refreshed"}
```

---

## Error Handling

### Command Not Found

```json
{
  "success": false,
  "error": "Unknown command: INVALID_COMMAND"
}
```

### Internal Error

```json
{
  "success": false,
  "error": "AttributeError: 'NoneType' object has no attribute..."
}
```

## Performance Characteristics

| Command | Thread | Typical Latency |
|---------|--------|-----------------|
| GET_VIEW | Socket thread | < 1ms |
| GET_STATE | Main thread | 20-50ms |
| SELECT_FIRST_SCENE | Main thread | 20-50ms |
| SELECT_LAST_SCENE | Main thread | 20-50ms |
| SELECT_FIRST_TRACK | Main thread | 20-50ms |
| SELECT_LAST_TRACK | Main thread | 20-50ms |
| GET_OBSERVER_STATUS | Main thread | 20-50ms |
| START_OBSERVERS | Main thread | 20-50ms |
| STOP_OBSERVERS | Main thread | 20-50ms |
| REFRESH_OBSERVERS | Main thread | 50-100ms |

## Adding Custom Commands

See the [Development Guide](../development/extending.md) for how to add your own commands.

## See Also

- [Lua API](lua-api.md) - Hammerspoon wrapper functions
- [OSC Protocol](osc-protocol.md) - UDP/OSC event reference
- [Architecture](../architecture/overview.md) - System architecture
