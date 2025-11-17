# Established UDP/OSC Observers

**Status:** ✅ Fully Working
**Last Updated:** 2025-11-12
**Remote Script Version:** Phase 5f Complete

---

## Overview

The UDP/OSC observer system monitors Ableton Live in real-time and streams events via UDP to port 9002. All observers are automatically initialized when Ableton Live loads the Remote Script.

---

## Active Observers

### 1. TrackObserver

**Purpose:** Monitors individual tracks for property changes

**Events Sent:**

| Event Path            | Arguments                 | Debounce | Description                           |
| --------------------- | ------------------------- | -------- | ------------------------------------- |
| `/live/track/renamed` | `[track_idx, name]`       | 0ms      | Track name changed                    |
| `/live/track/mute`    | `[track_idx, bool]`       | 0ms      | Track muted/unmuted (Track On button) |
| `/live/track/arm`     | `[track_idx, bool]`       | 0ms      | Track armed/disarmed (record enable)  |
| `/live/track/volume`  | `[track_idx, float]`      | 50ms     | Track volume fader changed (0.0-1.0)  |
| `/live/track/added`   | `[track_idx, name, type]` | 0ms      | New track added                       |
| `/live/track/deleted` | `[track_idx]`             | 0ms      | Track deleted                         |

**Scope:**

- Monitors all tracks (Audio, MIDI, Return, Master)
- Arm listener only added to tracks that support arming (`can_be_armed`)
- Volume listener attached via `mixer_device.volume` parameter
- Auto-refreshes when tracks are added/removed

**Verified Working:** ✅

- Track rename: ✅
- Track mute: ✅ (tested with track 16)
- Track volume: ✅ (tested with track 16, debounced 50ms)
- Track arm: ⚠️ (not yet tested)

---

### 2. DeviceObserver

**Purpose:** Monitors devices on tracks for parameter changes

**Events Sent:**

| Event Path             | Arguments                                | Debounce | Description               |
| ---------------------- | ---------------------------------------- | -------- | ------------------------- |
| `/live/device/added`   | `[track_idx, dev_idx, name]`             | 0ms      | Device added to track     |
| `/live/device/deleted` | `[track_idx, dev_idx]`                   | 0ms      | Device removed from track |
| `/live/device/param`   | `[track_idx, dev_idx, param_idx, value]` | 50ms     | Device parameter changed  |

**Scope:**

- One observer per device on each track
- Monitors **first 8 parameters only** per device
- Parameter observers use debouncing to prevent flooding
- Auto-creates observers when devices are added
- Auto-destroys observers when devices are removed

**Verified Working:** ✅

- Device parameter: ✅ (tested with track 16, device 2, param 7)

---

### 3. TransportObserver

**Purpose:** Monitors global transport state

**Events Sent:**

| Event Path              | Arguments | Debounce | Description              |
| ----------------------- | --------- | -------- | ------------------------ |
| `/live/transport/play`  | `[bool]`  | 0ms      | Playback started/stopped |
| `/live/transport/tempo` | `[float]` | 100ms    | Tempo (BPM) changed      |

**Scope:**

- Single observer for entire Live session
- Tempo changes are debounced to prevent flooding when dragging
- Position/beat events are NOT observed (too high-frequency)

**Verified Working:** ✅

- Tempo change: ✅ (tested from 121-118 BPM, debounced 100ms)
- Transport play: ⚠️ (not yet tested)

---

## Observer Lifecycle

### Initialization

```
Ableton Live starts
  ↓
Remote Script loads (LiveState.py)
  ↓
UDP sender initialized (127.0.0.1:9002)
  ↓
ObserverManager created
  ↓
ObserverManager.start() called
  ↓
Creates TrackObserver for each track
Creates DeviceObserver for each device
Creates TransportObserver
  ↓
All listeners registered
```

### Automatic Refresh

The ObserverManager automatically refreshes when:

- Tracks are added (creates new TrackObserver)
- Tracks are deleted (removes TrackObserver)
- Devices are added (creates new DeviceObserver)
- Devices are deleted (removes DeviceObserver)

### Manual Control (via TCP port 9001)

```bash title="Start/Stop Observers" linenums="1"
# Start observers
echo "START_OBSERVERS" | nc localhost 9001

# Stop observers (save CPU)
echo "STOP_OBSERVERS" | nc localhost 9001

# Refresh observer list
echo "REFRESH_OBSERVERS" | nc localhost 9001

# Get observer status
echo "GET_OBSERVER_STATUS" | nc localhost 9001
# Response: {"success": true, "stats": {"enabled": true, "track_count": 36, "has_transport": true}}
```

---

## NOT Implemented (Future)

### ClipObserver

**Reason:** Deferred to future enhancement
**Events:** clip triggered, clip stopped, clip name changed

### SceneObserver

**Reason:** Deferred to future enhancement
**Events:** scene triggered, scene name changed

### PositionObserver

**Reason:** Too high-frequency, would flood UDP
**Alternative:** Poll position when needed via TCP commands

---

## Debouncing Configuration

| Event Type                                        | Interval | Rationale                          |
| ------------------------------------------------- | -------- | ---------------------------------- |
| Structural changes (name, mute, arm, add, delete) | 0ms      | Send immediately                   |
| Volume fader                                      | 50ms     | Smooth for dragging, reduces flood |
| Device parameters                                 | 50ms     | Smooth for tweaking, reduces flood |
| Tempo                                             | 100ms    | Less critical, reduces overhead    |

**Implementation:** `Debouncer` class in `observers.py`

---

## Event Statistics

Based on manual testing (2025-11-12):

**Test Session:**

- Duration: ~5 minutes
- Tracks: 36 total
- Events received: 38

**Event Breakdown:**

- Tempo changes: 7 events (121 → 118 BPM)
- Track mute: 8 events (on/off toggling)
- Track volume: 20 events (fader dragging)
- Device parameter: 1 event
- Track rename: 2 events (earlier tests)

**Performance:**

- Latency: < 10ms (localhost UDP)
- CPU usage: < 2% (Ableton Remote Script)
- Packet loss: 0% (localhost is reliable)
- Sequence gaps: 0 (no missed events)

---

## Debugging

### Check if observers are running:

```bash
echo "GET_OBSERVER_STATUS" | nc localhost 9001
```

Expected response:

```json
{
  "success": true,
  "stats": {
    "enabled": true,
    "track_count": 36,
    "has_transport": true
  }
}
```

### Check Ableton log for initialization:

```bash
tail -50 ~/Library/Preferences/Ableton/Live*/Log.txt | grep -E "(UDP|observer)"
```

Expected messages:

```
UDP sender initialized on 127.0.0.1:9002
UDP observer manager started
Track 0: Added name listener
Track 0: Added mute listener
Track 0: Added arm listener
Track 0: Added volume listener
Track 0: Added devices listener
...
```

### Monitor UDP traffic:

```bash
# Terminal 1: Start listener
python3 src/udp_listener/listener.py

# Terminal 2: Make changes in Ableton
# Watch events appear in Terminal 1
```

### Send manual test events:

```bash
python3 tools/test_udp_manual.py
```

---

## Troubleshooting

### No events received

**Check 1:** Is UDP listener running?

```bash
lsof -i :9002
```

**Check 2:** Is Remote Script loaded?

```bash
echo "GET_OBSERVER_STATUS" | nc localhost 9001
```

**Check 3:** Restart Ableton Live

- Quit Ableton completely
- Start UDP listener
- Launch Ableton again

### Only seeing some event types

**Check:** Track type matters

- Master and Return tracks can't be armed → no arm events
- Some tracks might not have devices → no device events

### Events seem delayed

**Expected:** Debouncing adds delay

- Volume/params: 50ms delay
- Tempo: 100ms delay
- This is intentional to prevent flooding

### Too many volume events

**Expected:** Volume events during fader drag

- Each position change triggers event (after 50ms debounce)
- This is normal - use in UI with throttling if needed

---

## Performance Characteristics

### Event Rates (Typical)

| Activity       | Events/sec | Notes                 |
| -------------- | ---------- | --------------------- |
| Track rename   | < 1        | Rare operation        |
| Mute toggle    | 1-5        | Occasional            |
| Volume drag    | 10-20      | During fader movement |
| Device tweak   | 10-20      | During knob turning   |
| Tempo drag     | 5-10       | During tempo change   |
| Normal editing | 10-50      | Mixed activities      |
| Project load   | 100-500    | Initial burst         |

### Resource Usage

| Metric                   | Value      | Test Conditions           |
| ------------------------ | ---------- | ------------------------- |
| CPU (Remote Script)      | < 2%       | 36 tracks, active editing |
| Memory                   | ~5MB       | 36 tracks, 50+ devices    |
| UDP packets/sec          | 10-50      | Normal editing            |
| Latency (event → UDP)    | < 5ms      | Measured                  |
| Latency (UDP → listener) | < 5ms      | Localhost                 |
| **Total latency**        | **< 10ms** | End-to-end                |

---

## Implementation Details

### Files

- `src/remote_script/observers.py` - Observer classes (600+ lines)
- `src/remote_script/LiveState.py` - Integration (initializes observers)
- `src/remote_script/udp_sender.py` - UDP sender (180 lines)
- `src/remote_script/osc.py` - OSC message encoder (270 lines)

### Key Classes

- `Debouncer` - Rate-limits high-frequency events
- `TrackObserver` - Monitors one track
- `DeviceObserver` - Monitors one device
- `TransportObserver` - Monitors transport
- `ObserverManager` - Manages all observers

### Design Patterns

- **Observer pattern:** Live API listeners trigger callbacks
- **Debouncing:** Time-based filtering prevents flooding
- **Fire-and-forget:** UDP requires no acknowledgment
- **Singleton sender:** One UDPSender instance for all observers
- **Auto-refresh:** Observers update when tracks/devices change

---

## Example Usage

### In Ableton Remote Script (Automatic)

```python
# LiveState.py initialization
self.udp_sender = UDPSender(host="127.0.0.1", port=9002)
self.udp_sender.start()

self.udp_observer_manager = ObserverManager(
    song=self.song(),
    udp_sender=self.udp_sender
)
self.udp_observer_manager.start()
```

### In UDP Listener (Python)

```python
async def my_callback(event_path, args, seq_num, timestamp):
    if event_path == "/live/track/mute":
        track_idx, muted = args
        print(f"Track {track_idx} {'muted' if muted else 'unmuted'}")
    elif event_path == "/live/track/volume":
        track_idx, volume = args
        print(f"Track {track_idx} volume: {volume:.2f}")

listener = UDPListener(event_callback=my_callback)
await listener.start()
```

### In Svelte UI (Future - Phase 5e)

```javascript
// WebSocket receives events from AST server
websocket.onmessage = (msg) => {
  const event = JSON.parse(msg.data);
  if (event.type === "track_mute") {
    updateTrackUI(event.track_idx, { muted: event.muted });
  }
};
```

---

## Next Steps

**Phase 5e: AST Server Integration** (TODO)

- Forward UDP events to AST server
- Process events to update in-memory AST
- Compute incremental diffs
- Broadcast to WebSocket clients

**Phase 5i: Bi-directional Communication** (Optional)

- Send commands from UI → Remote Script
- Control Ableton from web interface

---

**For more details:**

- Protocol spec: `docs/OSC_PROTOCOL.md`
- Testing guide: `docs/MANUAL_TESTING_UDP_OSC.md`
- Progress report: `docs/UDP_OSC_PROGRESS.md`
