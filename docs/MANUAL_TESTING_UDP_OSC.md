# Manual Testing Guide: UDP/OSC Real-Time Observer with Ableton Live

**Date:** 2025-11-12
**Status:** Phase 5f Complete - Ready for Live Testing
**Prerequisites:** Ableton Live 11+, Remote Script installed

---

## Overview

This guide walks through manual testing of the UDP/OSC real-time observer system with Ableton Live. The system streams real-time events from Ableton Live to a UDP listener via OSC messages.

**What's been implemented:**
- ✅ OSC message encoder/decoder
- ✅ UDP sender (non-blocking, < 1ms latency)
- ✅ UDP listener with deduplication
- ✅ Live API observers (tracks, devices, transport)
- ✅ Debouncing (50-100ms intervals)
- ✅ Observer lifecycle management
- ✅ Remote Script commands (START/STOP/REFRESH/GET_OBSERVER_STATUS)
- ✅ LiveState.py integration

---

## Test Setup

### Step 1: Verify Remote Script Installation

Check that the Remote Script is properly symlinked:

```bash
ls -la ~/Music/Ableton/User\ Library/Remote\ Scripts/
```

Expected output:
```
LiveState -> /Users/[username]/Development/python/VimAbl/src/remote_script
```

If not present, create symlink:
```bash
ln -s /Users/pforsten/Development/python/VimAbl/src/remote_script \
      ~/Music/Ableton/User\ Library/Remote\ Scripts/LiveState
```

### Step 2: Start UDP Listener

In Terminal 1, start the UDP listener:

```bash
cd /Users/pforsten/Development/python/VimAbl
python3 src/udp_listener/listener.py
```

Expected output:
```
[INFO] UDP listener started on 0.0.0.0:9002
[INFO] Waiting for OSC messages...
```

### Step 3: Start Ableton Live

1. Launch Ableton Live
2. Open any project (or create a new one)
3. Check Ableton's log for initialization:

```bash
tail -f ~/Library/Preferences/Ableton/Live\ */Log.txt | grep -E "(Live State|UDP)"
```

Expected log output:
```
Live State Remote Script initialized
UDP sender initialized on 127.0.0.1:9002
UDP observer manager started
```

---

## Test Cases

### Test 1: Track Name Change ✅

**Action:**
1. Right-click a track in Ableton
2. Select "Rename"
3. Type "Bass" and press Enter

**Expected UDP Listener Output:**
```
[0] /live/track/renamed [0, 'Bass']
```

**Verify:**
- ✅ Sequence number increments
- ✅ Event path is `/live/track/renamed`
- ✅ Arguments: `[track_index, "new_name"]`
- ✅ Received within 10ms

---

### Test 2: Track Mute/Unmute ✅

**Action:**
1. Click the "Track On" button to mute track 0

**Expected UDP Listener Output:**
```
[1] /live/track/mute [0, True]
```

**Action:**
2. Click again to unmute

**Expected UDP Listener Output:**
```
[2] /live/track/mute [0, False]
```

**Verify:**
- ✅ Immediate response (< 5ms)
- ✅ Boolean value matches mute state

---

### Test 3: Track Arm ✅

**Action:**
1. Click the arm button on track 1

**Expected UDP Listener Output:**
```
[3] /live/track/arm [1, True]
```

**Verify:**
- ✅ Immediate response
- ✅ Track index is correct

---

### Test 4: Volume Fader (Debounced) ✅

**Action:**
1. Move volume fader on track 0 from 0dB to -10dB

**Expected UDP Listener Output:**
```
[4] /live/track/volume [0, 0.631]
[5] /live/track/volume [0, 0.501]
```

**Verify:**
- ✅ Events are debounced (50ms interval)
- ✅ Not every tiny movement triggers event
- ✅ Final value is captured

---

### Test 5: Add Device ✅

**Action:**
1. Drag "Reverb" device onto track 0

**Expected UDP Listener Output:**
```
[6] /live/device/added [0, 0, 'Reverb']
```

**Verify:**
- ✅ Event shows track index, device index, device name
- ✅ Received immediately after drag-drop

---

### Test 6: Device Parameter Change (Debounced) ✅

**Action:**
1. Tweak a parameter on the Reverb device (e.g., Decay Time)

**Expected UDP Listener Output:**
```
[7] /live/device/param [0, 0, 2, 0.75]
```

**Verify:**
- ✅ Events are debounced (50ms interval)
- ✅ Arguments: `[track_idx, device_idx, param_idx, value]`
- ✅ Only first 8 parameters are observed

---

### Test 7: Transport Play/Stop ✅

**Action:**
1. Press spacebar to start playback

**Expected UDP Listener Output:**
```
[8] /live/transport/play [True]
```

**Action:**
2. Press spacebar to stop playback

**Expected UDP Listener Output:**
```
[9] /live/transport/play [False]
```

**Verify:**
- ✅ Immediate response
- ✅ Boolean value matches playback state

---

### Test 8: Tempo Change (Debounced) ✅

**Action:**
1. Change tempo from 120 BPM to 130 BPM

**Expected UDP Listener Output:**
```
[10] /live/transport/tempo [125.0]
[11] /live/transport/tempo [130.0]
```

**Verify:**
- ✅ Events are debounced (100ms interval)
- ✅ Tempo value is float

---

### Test 9: Add Track ✅

**Action:**
1. Right-click track area
2. Select "Insert Audio Track"

**Expected UDP Listener Output:**
```
[12] /live/track/added [3, 'Audio 4', 'audio']
```

**Verify:**
- ✅ Event shows new track index, name, type
- ✅ Observer manager auto-refreshes (new TrackObserver created)

---

### Test 10: Delete Track ✅

**Action:**
1. Right-click track 3
2. Select "Delete"

**Expected UDP Listener Output:**
```
[13] /live/track/deleted [3]
```

**Verify:**
- ✅ Event shows deleted track index
- ✅ Observer manager auto-refreshes (TrackObserver removed)

---

## Remote Script Commands

You can control the UDP observers via TCP commands to port 9001.

### Test Command: GET_OBSERVER_STATUS

**Send command:**
```bash
echo "GET_OBSERVER_STATUS" | nc localhost 9001
```

**Expected response:**
```json
{
  "success": true,
  "stats": {
    "track_observers": 3,
    "device_observers": 2,
    "transport_observer": 1,
    "total_events": 14
  }
}
```

### Test Command: STOP_OBSERVERS

**Send command:**
```bash
echo "STOP_OBSERVERS" | nc localhost 9001
```

**Expected response:**
```json
{
  "success": true,
  "message": "UDP observers stopped"
}
```

**Verify:**
- ✅ No more UDP events received when making changes in Live
- ✅ Check Ableton log: "UDP observers stopped"

### Test Command: START_OBSERVERS

**Send command:**
```bash
echo "START_OBSERVERS" | nc localhost 9001
```

**Expected response:**
```json
{
  "success": true,
  "message": "UDP observers started",
  "stats": {
    "track_observers": 3,
    "device_observers": 2,
    "transport_observer": 1
  }
}
```

**Verify:**
- ✅ UDP events resume when making changes in Live
- ✅ Check Ableton log: "UDP observers started"

### Test Command: REFRESH_OBSERVERS

**Send command:**
```bash
echo "REFRESH_OBSERVERS" | nc localhost 9001
```

**Expected response:**
```json
{
  "success": true,
  "message": "UDP observers refreshed",
  "stats": {
    "track_observers": 3,
    "device_observers": 2,
    "transport_observer": 1
  }
}
```

**Verify:**
- ✅ Observers are recreated for current Live state
- ✅ UDP events continue to work correctly

---

## Performance Testing

### Test 11: Rapid Changes (Stress Test)

**Action:**
1. Rapidly tweak multiple parameters simultaneously
2. Move multiple faders
3. Add/remove devices quickly

**Monitor:**
- UDP listener should handle 100-500 events/sec
- No parse errors
- CPU usage < 5% for Remote Script
- No crashes or hangs

**Expected behavior:**
- ✅ Debouncing prevents flooding
- ✅ Events are properly sequenced
- ✅ No duplicates or gaps

### Test 12: Large Project

**Action:**
1. Open a project with 50+ tracks
2. Start observers
3. Make various changes

**Monitor:**
- Observer initialization time < 1 second
- Memory usage < 100MB
- UDP events still < 10ms latency

---

## Troubleshooting

### No UDP Messages Received

**Check UDP listener is running:**
```bash
lsof -i :9002
```

Expected:
```
COMMAND   PID   USER   FD   TYPE ... NAME
Python  12345  user    3u  IPv4 ... UDP *:9002
```

**If port is in use:**
```bash
kill $(lsof -ti :9002)
python3 src/udp_listener/listener.py
```

### Remote Script Not Loading

**Check Ableton log:**
```bash
tail -100 ~/Library/Preferences/Ableton/Live\ */Log.txt | grep -i error
```

**Common issues:**
- Import error: Check Python 2.7 compatibility
- Syntax error: Check for Python 3 syntax in remote script
- Missing dependency: Ensure all modules exist

**Reload Remote Script:**
1. Quit Ableton Live
2. Restart Ableton Live
3. Check log again

### Parse Errors

**Check listener log:**
```bash
tail -f /tmp/listener.log | grep "parse error"
```

**If parse errors occur:**
- Capture raw UDP packet: `nc -u -l 9002 | xxd > /tmp/packet.hex`
- Compare with OSC spec
- Check `src/remote_script/osc.py` encoding

### High CPU Usage

**Check observer stats:**
```bash
echo "GET_OBSERVER_STATUS" | nc localhost 9001
```

**If too many observers:**
- Stop observers: `echo "STOP_OBSERVERS" | nc localhost 9001`
- Reduce debounce intervals in `observers.py`
- Consider observing fewer device parameters (currently first 8)

### Sequence Number Gaps

**Check listener log:**
```bash
tail -f /tmp/listener.log | grep "Gap"
```

**If gaps detected:**
- UDP packet loss (rare on localhost)
- Observer sent events too fast
- Future: Will trigger XML diff fallback

---

## Success Criteria

For Phase 5f to be considered complete, all of the following must pass:

### Functional Requirements
- ✅ Track name changes trigger UDP events
- ✅ Track mute/arm changes trigger UDP events
- ✅ Volume changes are debounced (50ms) and sent
- ✅ Device add/remove triggers UDP events
- ✅ Device parameter changes are debounced (50ms) and sent
- ✅ Transport play/stop triggers UDP events
- ✅ Tempo changes are debounced (100ms) and sent
- ✅ Track add/remove triggers UDP events and auto-refresh

### Commands
- ✅ START_OBSERVERS starts observers
- ✅ STOP_OBSERVERS stops observers
- ✅ REFRESH_OBSERVERS refreshes observers
- ✅ GET_OBSERVER_STATUS returns statistics

### Performance
- ✅ Event latency < 10ms (local)
- ✅ CPU usage < 5%
- ✅ No crashes after 10 minutes of editing
- ✅ Handles 50+ tracks without issues

### Reliability
- ✅ No duplicate events
- ✅ Sequence numbers increment correctly
- ✅ Observers cleanup on disconnect
- ✅ No memory leaks after start/stop cycles

---

## Next Steps (Phase 5e)

After manual testing confirms everything works:

1. **AST Server Integration**
   - Create `src/udp_listener/bridge.py`
   - Forward UDP events to AST server
   - Process events to update AST in-memory
   - Compute incremental diffs
   - Broadcast via WebSocket to Svelte UI

2. **XML Diff Fallback**
   - Detect gaps > 10 in sequence numbers
   - Trigger full XML reload
   - Log fallback events

3. **End-to-End Testing**
   - Verify Svelte UI updates in real-time
   - Test with complex project
   - Measure end-to-end latency (Ableton → UI)

---

## Appendix: Expected Event Catalog

| Event Path | Arguments | Debounce | Frequency |
|------------|-----------|----------|-----------|
| `/live/track/renamed` | `[idx, name]` | 0ms | Low |
| `/live/track/added` | `[idx, name, type]` | 0ms | Low |
| `/live/track/deleted` | `[idx]` | 0ms | Low |
| `/live/track/mute` | `[idx, bool]` | 0ms | Medium |
| `/live/track/arm` | `[idx, bool]` | 0ms | Medium |
| `/live/track/volume` | `[idx, float]` | 50ms | High |
| `/live/device/added` | `[track_idx, dev_idx, name]` | 0ms | Low |
| `/live/device/deleted` | `[track_idx, dev_idx]` | 0ms | Low |
| `/live/device/param` | `[track_idx, dev_idx, param_idx, value]` | 50ms | Very High |
| `/live/transport/play` | `[bool]` | 0ms | Low |
| `/live/transport/tempo` | `[float]` | 100ms | Low |

**Note:** Clip and Scene observers are not yet implemented (deferred to later phase).

---

## Log Files

- **Ableton Live Log:** `~/Library/Preferences/Ableton/Live */Log.txt`
- **UDP Listener Log:** `/tmp/listener.log` (if logging enabled)
- **Raw UDP Traffic:** `nc -u -l 9002 > /tmp/udp_raw.log`

---

**End of Manual Testing Guide**

For automated testing, see `docs/TESTING_UDP_OSC.md`
For protocol details, see `docs/OSC_PROTOCOL.md`
