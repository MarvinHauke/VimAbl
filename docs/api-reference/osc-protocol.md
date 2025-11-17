# UDP/OSC Real-Time Observer Protocol

## Overview

This document describes the UDP/OSC protocol used for real-time communication between the Ableton Live Remote Script and the AST Server. The protocol enables low-latency (<1ms) event streaming without blocking Ableton's main thread.

## Architecture

```
                     (A) .als file watcher
          ┌────────────────────────────────┐
          │  Python AST Server (Port 8765) │
          │  - Maintains AST               │
          │  - Computes diffs              │
          │  - WebSocket broadcast to UI   │
          └──────────┬─────────────────────┘
                     ▲
   (D) UDP/OSC ⇡     │  ⇣ WebSocket (to Svelte)
      Port 9002      │
                     ▼
          ┌────────────────────────────────┐
          │  UDP Listener Bridge           │
          │  - Receives OSC events         │
          │  - Deduplicates messages       │
          │  - Forwards to AST server      │
          └──────────┬─────────────────────┘
                     ▲
   UDP (fire & forget, < 1ms latency)
                     │
          ┌──────────┴─────────────────────┐
          │  Ableton Remote Script         │
          │  - Live API observers          │
          │  - Emits OSC/UDP events        │
          │  - Debounces rapid changes     │
          └────────────────────────────────┘
```

## Port Allocation

| Port | Service | Protocol | Purpose |
|------|---------|----------|---------|
| 9001 | Remote Script TCP Server | TCP | Command interface (existing) |
| 9002 | UDP Listener | UDP | Real-time events (new) |
| 8765 | WebSocket Server | WebSocket | AST streaming to UI (existing) |

## Why UDP/OSC?

### Advantages
- ✅ **Ultra-low latency** - < 1ms, fire-and-forget
- ✅ **Non-blocking** - Remote Script never waits for acknowledgment
- ✅ **Ableton-friendly** - Same pattern as Max for Live, TouchOSC, OSCulator
- ✅ **Lightweight** - Just `socket.sendto()` in Python
- ✅ **Easy to debug** - Standard OSC tools work (oscdump, Wireshark)
- ✅ **No dependencies** - Uses Python's built-in `socket` module

### Disadvantages
- ⚠️ **Unreliable** - UDP packets can be lost or arrive out of order
- ⚠️ **No acknowledgment** - Sender doesn't know if receiver got the message
- ⚠️ **Size limits** - UDP packets limited to ~64KB (not an issue for our small messages)

### Mitigation Strategy
- **Sequence numbers** - Detect missing messages and gaps
- **Deduplication** - Ignore duplicate packets (in case of network retransmit)
- **XML diff fallback** - If gaps detected, trigger full XML reload and diff
- **Debouncing** - Coalesce rapid changes to reduce packet count

## OSC Message Format

### Standard OSC Message Structure

```
┌──────────────────────────────────────────┐
│  OSC Address Pattern (null-terminated)   │  e.g., "/live/track/renamed\0\0"
├──────────────────────────────────────────┤
│  OSC Type Tag String (null-terminated)   │  e.g., ",is\0"
├──────────────────────────────────────────┤
│  Argument 1 (4-byte aligned)             │  e.g., int32: 0
├──────────────────────────────────────────┤
│  Argument 2 (4-byte aligned)             │  e.g., string: "Bass\0\0\0"
└──────────────────────────────────────────┘
```

### OSC Type Tags
- `i` - 32-bit integer (int32)
- `f` - 32-bit float (float32)
- `s` - String (null-terminated, padded to 4-byte boundary)
- `T` - Boolean True
- `F` - Boolean False

### Sequence Number Wrapper

All events are wrapped with sequence metadata:

```
/live/seq <seq_num:int> <timestamp:float> <event_path:str> <args...>
```

**Example:**
```
/live/seq 42 1234567890.123 /live/track/renamed 0 "New Track Name"
```

## Message Catalog

### Track Events

#### Track Renamed
```
/live/track/renamed <track_idx:int> <name:str>
```
**Example:** `/live/track/renamed 0 "Bass"`
**When:** User renames a track in Live
**OSC Types:** `,is` (int, string)

#### Track Added
```
/live/track/added <track_idx:int> <name:str> <type:str>
```
**Example:** `/live/track/added 3 "Audio 4" "audio"`
**When:** User creates a new track
**OSC Types:** `,iss` (int, string, string)
**Types:** `"audio"`, `"midi"`, `"return"`, `"master"`

#### Track Deleted
```
/live/track/deleted <track_idx:int>
```
**Example:** `/live/track/deleted 2`
**When:** User deletes a track
**OSC Types:** `,i` (int)

#### Track Mute
```
/live/track/mute <track_idx:int> <muted:bool>
```
**Example:** `/live/track/mute 0 T`
**When:** User toggles track mute
**OSC Types:** `,iT` or `,iF` (int, bool)

#### Track Arm
```
/live/track/arm <track_idx:int> <armed:bool>
```
**Example:** `/live/track/arm 1 T`
**When:** User arms/disarms a track for recording
**OSC Types:** `,iT` or `,iF` (int, bool)

#### Track Volume
```
/live/track/volume <track_idx:int> <volume:float>
```
**Example:** `/live/track/volume 0 0.85`
**When:** User changes track volume
**OSC Types:** `,if` (int, float)
**Range:** 0.0 (silent) to 1.0 (0dB)
**Debouncing:** 50ms minimum interval

### Device Events

#### Device Added
```
/live/device/added <track_idx:int> <device_idx:int> <name:str>
```
**Example:** `/live/device/added 0 2 "Reverb"`
**When:** User adds a device to a track
**OSC Types:** `,iis` (int, int, string)

#### Device Deleted
```
/live/device/deleted <track_idx:int> <device_idx:int>
```
**Example:** `/live/device/deleted 0 1`
**When:** User removes a device from a track
**OSC Types:** `,ii` (int, int)

#### Device Parameter Changed
```
/live/device/param <track_idx:int> <device_idx:int> <param_id:int> <value:float>
```
**Example:** `/live/device/param 0 1 3 0.75`
**When:** User tweaks a device parameter
**OSC Types:** `,iiif` (int, int, int, float)
**Debouncing:** 50ms minimum interval per parameter

### Clip Events

#### Clip Triggered
```
/live/clip/triggered <track_idx:int> <scene_idx:int>
```
**Example:** `/live/clip/triggered 0 2`
**When:** User launches a clip
**OSC Types:** `,ii` (int, int)

#### Clip Stopped
```
/live/clip/stopped <track_idx:int> <scene_idx:int>
```
**Example:** `/live/clip/stopped 0 2`
**When:** Clip stops playing
**OSC Types:** `,ii` (int, int)

#### Clip Added
```
/live/clip/added <track_idx:int> <scene_idx:int> <name:str>
```
**Example:** `/live/clip/added 1 0 "Drums"`
**When:** User creates a new clip
**OSC Types:** `,iis` (int, int, string)

#### Clip Deleted
```
/live/clip/deleted <track_idx:int> <scene_idx:int>
```
**Example:** `/live/clip/deleted 1 0`
**When:** User deletes a clip
**OSC Types:** `,ii` (int, int)

### Scene Events

#### Scene Renamed
```
/live/scene/renamed <scene_idx:int> <name:str>
```
**Example:** `/live/scene/renamed 0 "Intro"`
**When:** User renames a scene
**OSC Types:** `,is` (int, string)

#### Scene Triggered
```
/live/scene/triggered <scene_idx:int>
```
**Example:** `/live/scene/triggered 2`
**When:** User launches an entire scene
**OSC Types:** `,i` (int)

### Transport Events

#### Transport Play/Stop
```
/live/transport/play <is_playing:bool>
```
**Example:** `/live/transport/play T`
**When:** User starts/stops playback
**OSC Types:** `,T` or `,F` (bool)

#### Transport Tempo
```
/live/transport/tempo <bpm:float>
```
**Example:** `/live/transport/tempo 128.0`
**When:** User changes tempo
**OSC Types:** `,f` (float)
**Debouncing:** 100ms minimum interval

#### Transport Position
```
/live/transport/position <beats:float>
```
**Example:** `/live/transport/position 64.5`
**When:** Playhead moves (HEAVILY DEBOUNCED)
**OSC Types:** `,f` (float)
**Debouncing:** 500ms minimum interval (or disable entirely)

### Batch Events

Used to group multiple related changes into a single logical update.

#### Batch Start
```
/live/batch/start <batch_id:int>
```
**Example:** `/live/batch/start 1001`
**When:** Beginning of a multi-event operation (e.g., loading a project)
**OSC Types:** `,i` (int)

#### Batch End
```
/live/batch/end <batch_id:int>
```
**Example:** `/live/batch/end 1001`
**When:** End of a multi-event operation
**OSC Types:** `,i` (int)

**Use case:** When a project loads, group all the "track added" events into a batch so the UI can update once instead of flickering.

## Sequence Numbers

### Format
Every message includes a sequence number in the wrapper:
```
/live/seq <seq_num:int> <timestamp:float> <event_path:str> <args...>
```

### Properties
- **Monotonically increasing** - Each message increments the sequence number
- **Starts at 0** - First message after Remote Script startup
- **Wraps at 2^31** - After ~2 billion messages (unlikely in practice)
- **Reset on restart** - Sequence resets when Ableton restarts

### Deduplication Algorithm

The UDP Listener maintains a circular buffer of recently seen sequence numbers:

```python
class SequenceTracker:
    def __init__(self, buffer_size=100):
        self.last_seq = -1
        self.seen = set()  # Recent sequence numbers
        self.buffer_size = buffer_size

    def is_duplicate(self, seq_num):
        if seq_num in self.seen:
            return True  # Duplicate

        # Add to seen set
        self.seen.add(seq_num)

        # Keep buffer size bounded
        if len(self.seen) > self.buffer_size:
            # Remove oldest entries (approximation)
            self.seen = set(list(self.seen)[-self.buffer_size:])

        return False

    def detect_gap(self, seq_num):
        if self.last_seq == -1:
            self.last_seq = seq_num
            return 0  # No gap on first message

        expected = self.last_seq + 1
        gap = seq_num - expected
        self.last_seq = seq_num

        if gap > 0:
            return gap  # Messages were lost
        elif gap < -1:
            return 0  # Out of order, but within tolerance
        else:
            return 0  # Normal sequential message
```

### Gap Handling

When a gap is detected:
1. **Log warning** - Record the gap size and sequence numbers
2. **Continue processing** - Don't drop the message just because of a gap
3. **Trigger fallback** - If gap > 10 messages, trigger full XML reload
4. **Update UI** - Show yellow warning indicator in UI

## Debouncing Strategy

### Why Debounce?
Some Live events fire extremely rapidly (e.g., volume faders, playhead position). Without debouncing, we'd flood the network with thousands of messages per second.

### Debounce Configuration

| Event Type | Min Interval | Rationale |
|------------|--------------|-----------|
| Track volume | 50ms | Smooth enough for UI, reduces flood |
| Device parameters | 50ms | Smooth enough for UI, reduces flood |
| Transport position | 500ms | Rarely needed in real-time UI |
| Track rename | 0ms | Infrequent, send immediately |
| Device add/remove | 0ms | Infrequent, send immediately |
| Clip trigger/stop | 0ms | Time-critical, send immediately |

### Debounce Implementation

```python
class Debouncer:
    def __init__(self):
        self.last_send_time = {}  # event_key -> timestamp

    def should_send(self, event_key, min_interval_ms):
        now = time.time()
        last = self.last_send_time.get(event_key, 0)

        if (now - last) * 1000 >= min_interval_ms:
            self.last_send_time[event_key] = now
            return True
        else:
            return False  # Too soon, skip this event
```

**Event key format:** `"{event_type}:{track_idx}:{param_id}"`

**Example:** Volume change on track 0 → `"track.volume:0"`

## Testing & Debugging

### Monitor UDP Traffic with netcat

```bash
# Listen for UDP packets on port 9002
nc -u -l 9002
```

### Monitor with OSC Tools

```bash
# Install oscdump (if available)
brew install liblo

# Monitor OSC messages
oscdump 9002
```

### Send Test Messages

```bash
# Install python-osc
pip install python-osc

# Send test message
python tools/osc_send.py /live/track/renamed 0 "Test Track"
```

### Use Wireshark

1. Start Wireshark capture on loopback interface (`lo0`)
2. Filter: `udp.port == 9002`
3. Right-click packet → Decode As → OSC
4. View OSC message contents

### Check Ableton Log

```bash
tail -f ~/Library/Preferences/Ableton/Live\ */Log.txt | grep "UDP"
```

## Fallback to XML Diff

### When to Fallback

UDP is unreliable, so we need a fallback mechanism to ensure consistency:

1. **Gap detection** - If sequence number gap > 10
2. **Hash mismatch** - If AST hash doesn't match after applying UDP events
3. **Periodic validation** - Every 60 seconds, compare UDP-derived AST with XML
4. **Manual trigger** - User can force full refresh via UI button

### Fallback Procedure

1. **Detect inconsistency** - Gap, hash mismatch, or timeout
2. **Log event** - Record the reason for fallback
3. **Request XML export** - Send `EXPORT_XML` command via TCP (port 9001)
4. **Parse XML** - Load full project XML
5. **Compute diff** - Compare UDP-derived AST with XML-derived AST
6. **Broadcast diff** - Send corrected diff to WebSocket clients
7. **Update UI indicator** - Show "Synced via XML" message

### Monitoring Fallback Rate

Track fallback statistics:
- **Fallback count** - How many times did we fall back?
- **Fallback reason** - Gap, hash mismatch, or periodic?
- **Average gap size** - How many messages were lost?

**Target:** < 1 fallback per hour under normal use

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| End-to-end latency | < 100ms | From Live event to UI update |
| UDP send time | < 1ms | Fire-and-forget, non-blocking |
| Packet loss rate | < 0.1% | Local UDP is very reliable |
| CPU overhead (Remote Script) | < 1% | Minimal observer overhead |
| CPU overhead (UDP Listener) | < 2% | Parsing and forwarding |
| Events per second | 100-1000 | Typical for active editing |
| Max burst rate | 5000/sec | During project load (batched) |

## Future Enhancements (Phase 9)

### ZeroMQ Migration

For production/distributed setups, consider migrating to ZeroMQ:

**Advantages:**
- ✅ Reliable delivery with automatic retries
- ✅ Built-in reconnection logic
- ✅ Message queuing during disconnect
- ✅ Multiple subscribers (PUB/SUB pattern)
- ✅ No need for sequence numbers or deduplication

**Disadvantages:**
- ❌ Requires `pyzmq` dependency in Remote Script
- ❌ Slightly higher latency (~5ms vs ~1ms)
- ❌ More complex to debug

**Decision:** Start with UDP/OSC for simplicity. Migrate to ZMQ if reliability becomes an issue.

---

## References

- [OSC Specification](http://opensoundcontrol.org/spec-1_0)
- [Max for Live OSC](https://docs.cycling74.com/max8/vignettes/live_osc_communication)
- [TouchOSC Protocol](https://hexler.net/touchosc/manual/protocol-osc)
- [Python OSC Library](https://python-osc.readthedocs.io/)

---

**Last Updated:** 2025-11-12
**Status:** Design complete, implementation pending
